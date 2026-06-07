"""Download files and text sent to the Telegram bot by the configured user."""

from __future__ import annotations

import json
import os
import re
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

from telegram_config import load_env, require_config, workspace_root

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".tif", ".tiff"}


def default_input_dir() -> Path:
    custom = os.environ.get("TELEGRAM_INPUT_DIR", "").strip()
    if custom:
        path = Path(custom)
        return path if path.is_absolute() else workspace_root() / path
    return workspace_root() / "input" / "telegram"


DEFAULT_INPUT_DIR = default_input_dir()
STATE_DIR = workspace_root() / ".telegram"
OFFSET_FILE = STATE_DIR / "offset.json"


@dataclass
class ReceivedItem:
    update_id: int
    message_id: int
    kind: str
    path: Path | None
    text: str
    caption: str
    received_at: str

    def to_json(self) -> str:
        payload = asdict(self)
        payload["path"] = str(self.path) if self.path else None
        return json.dumps(payload, ensure_ascii=False)


def _api_base(token: str) -> str:
    return f"https://api.telegram.org/bot{token}"


def _load_offset() -> int | None:
    if not OFFSET_FILE.exists():
        return None
    try:
        data = json.loads(OFFSET_FILE.read_text(encoding="utf-8"))
        value = data.get("offset")
        return int(value) if value is not None else None
    except (OSError, ValueError, json.JSONDecodeError):
        return None


def _save_offset(offset: int) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "offset": offset,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    OFFSET_FILE.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _chat_id_matches(chat: dict[str, Any], expected_chat_id: str) -> bool:
    chat_id = chat.get("id")
    if chat_id is None:
        return False
    return str(chat_id) == str(expected_chat_id)


def _safe_name(name: str, fallback: str) -> str:
    cleaned = re.sub(r"[^\w.\-]+", "_", name.strip(), flags=re.UNICODE)
    cleaned = cleaned.strip("._")
    return cleaned or fallback


def _pick_photo_file_id(photo_sizes: list[dict[str, Any]]) -> str | None:
    if not photo_sizes:
        return None
    best = max(photo_sizes, key=lambda item: item.get("file_size", 0))
    return best.get("file_id")


def _extension_for_item(kind: str, file_name: str | None, file_path: str | None) -> str:
    if file_name:
        suffix = Path(file_name).suffix.lower()
        if suffix:
            return suffix
    if file_path:
        suffix = Path(file_path).suffix.lower()
        if suffix:
            return suffix
    if kind == "photo":
        return ".jpg"
    return ".bin"


def _download_file(token: str, file_id: str, destination: Path) -> None:
    response = requests.get(
        f"{_api_base(token)}/getFile",
        params={"file_id": file_id},
        timeout=60,
    )
    response.raise_for_status()
    payload = response.json()
    if not payload.get("ok"):
        raise RuntimeError(payload)

    file_path = payload["result"]["file_path"]
    download_url = f"https://api.telegram.org/file/bot{token}/{file_path}"

    destination.parent.mkdir(parents=True, exist_ok=True)
    with requests.get(download_url, stream=True, timeout=120) as stream:
        stream.raise_for_status()
        with destination.open("wb") as handle:
            for chunk in stream.iter_content(chunk_size=64 * 1024):
                if chunk:
                    handle.write(chunk)


def _extract_items_from_message(
    token: str,
    update_id: int,
    message: dict[str, Any],
    output_dir: Path,
) -> list[ReceivedItem]:
    message_id = int(message["message_id"])
    text = message.get("text") or ""
    caption = message.get("caption") or ""
    received_at = datetime.fromtimestamp(
        message.get("date", int(time.time())),
        tz=timezone.utc,
    ).isoformat()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    items: list[ReceivedItem] = []

    attachments: list[tuple[str, str, str | None]] = []
    photo_file_id = _pick_photo_file_id(message.get("photo") or [])
    if photo_file_id:
        attachments.append(("photo", photo_file_id, None))

    document = message.get("document")
    if document:
        attachments.append(
            (
                "document",
                document["file_id"],
                document.get("file_name"),
            )
        )

    if not attachments and (text or caption):
        body = text or caption
        destination = output_dir / f"{stamp}-{message_id}.txt"
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(body + "\n", encoding="utf-8")
        item = ReceivedItem(
            update_id=update_id,
            message_id=message_id,
            kind="text",
            path=destination,
            text=text,
            caption=caption,
            received_at=received_at,
        )
        destination.with_suffix(".txt.meta.json").write_text(
            item.to_json() + "\n",
            encoding="utf-8",
        )
        items.append(item)
        return items

    for index, (kind, file_id, file_name) in enumerate(attachments, start=1):
        suffix = _extension_for_item(kind, file_name, None)
        if file_name:
            base_name = _safe_name(Path(file_name).stem, f"{kind}-{message_id}")
            filename = f"{base_name}{suffix}"
        else:
            filename = f"{stamp}-{message_id}-{kind}"
            if len(attachments) > 1:
                filename += f"-{index}"
            filename += suffix

        destination = output_dir / filename
        if destination.exists():
            destination = output_dir / f"{destination.stem}-{update_id}{destination.suffix}"

        _download_file(token, file_id, destination)
        meta_path = destination.with_suffix(destination.suffix + ".meta.json")
        item = ReceivedItem(
            update_id=update_id,
            message_id=message_id,
            kind=kind,
            path=destination,
            text=text,
            caption=caption,
            received_at=received_at,
        )
        meta_path.write_text(item.to_json() + "\n", encoding="utf-8")
        items.append(item)

    return items


def fetch_updates(
    token: str,
    offset: int | None = None,
    timeout: int = 0,
) -> list[dict[str, Any]]:
    params: dict[str, Any] = {"timeout": timeout}
    if offset is not None:
        params["offset"] = offset

    response = requests.get(
        f"{_api_base(token)}/getUpdates",
        params=params,
        timeout=max(30, timeout + 10),
    )
    response.raise_for_status()
    payload = response.json()
    if not payload.get("ok"):
        raise RuntimeError(payload)
    return payload.get("result", [])


def receive_new_items(
    output_dir: Path | None = None,
    *,
    wait_timeout: int = 0,
    dry_run: bool = False,
    ack: bool = False,
) -> list[ReceivedItem]:
    load_env()
    token, expected_chat_id = require_config()
    output_dir = (output_dir or DEFAULT_INPUT_DIR).resolve()
    offset = _load_offset()
    updates = fetch_updates(token, offset=offset, timeout=wait_timeout)

    received: list[ReceivedItem] = []
    next_offset = offset

    for update in updates:
        update_id = int(update["update_id"])
        next_offset = update_id + 1

        message = update.get("message") or update.get("edited_message")
        if not message:
            continue
        if not _chat_id_matches(message.get("chat") or {}, expected_chat_id):
            continue

        if dry_run:
            kind = "text"
            if message.get("photo"):
                kind = "photo"
            elif message.get("document"):
                kind = "document"
            received.append(
                ReceivedItem(
                    update_id=update_id,
                    message_id=int(message["message_id"]),
                    kind=kind,
                    path=None,
                    text=message.get("text") or "",
                    caption=message.get("caption") or "",
                    received_at=datetime.now(timezone.utc).isoformat(),
                )
            )
            continue

        items = _extract_items_from_message(token, update_id, message, output_dir)
        received.extend(items)

        if ack and items:
            try:
                send_ack(token, expected_chat_id, "Сообщение получено, начинаю обработку.")
            except requests.RequestException:
                pass

    if next_offset is not None and updates and not dry_run:
        _save_offset(next_offset)

    return received


def send_ack(token: str, chat_id: str, text: str) -> None:
    response = requests.post(
        f"{_api_base(token)}/sendMessage",
        json={"chat_id": chat_id, "text": text},
        timeout=30,
    )
    response.raise_for_status()


def latest_downloaded_file(output_dir: Path | None = None) -> Path | None:
    directory = (output_dir or DEFAULT_INPUT_DIR).resolve()
    if not directory.exists():
        return None

    candidates = [
        path
        for path in directory.iterdir()
        if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS.union({".pdf", ".zip"})
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda path: path.stat().st_mtime)
