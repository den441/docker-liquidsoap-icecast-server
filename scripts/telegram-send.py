#!/usr/bin/env python3
"""Send text, images, and documents to Telegram via Bot API."""

from __future__ import annotations

import argparse
import mimetypes
import os
import sys
from pathlib import Path

import requests

from telegram_config import load_env, require_config

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".tif", ".tiff"}
MAX_CAPTION_LEN = 1024


def send_text(token: str, chat_id: str, text: str, parse_mode: str | None) -> dict:
    payload: dict[str, str] = {"chat_id": chat_id, "text": text}
    if parse_mode:
        payload["parse_mode"] = parse_mode
    response = requests.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        json=payload,
        timeout=60,
    )
    response.raise_for_status()
    return response.json()


def send_attachment(
    token: str,
    chat_id: str,
    file_path: Path,
    caption: str | None,
    parse_mode: str | None,
    as_document: bool,
) -> dict:
    suffix = file_path.suffix.lower()
    use_document = as_document or suffix not in IMAGE_EXTENSIONS
    method = "sendDocument" if use_document else "sendPhoto"
    field = "document" if use_document else "photo"

    data: dict[str, str] = {"chat_id": chat_id}
    if caption:
        data["caption"] = caption[:MAX_CAPTION_LEN]
        if parse_mode:
            data["parse_mode"] = parse_mode

    mime_type = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
    with file_path.open("rb") as handle:
        files = {field: (file_path.name, handle, mime_type)}
        response = requests.post(
            f"https://api.telegram.org/bot{token}/{method}",
            data=data,
            files=files,
            timeout=120,
        )
    response.raise_for_status()
    return response.json()


def main() -> int:
    load_env()
    parser = argparse.ArgumentParser(
        description="Send a Telegram message and optional attachments."
    )
    parser.add_argument(
        "message",
        nargs="?",
        default="",
        help="Text message or caption for attachments.",
    )
    parser.add_argument(
        "files",
        nargs="*",
        help="Paths to images or documents to send.",
    )
    parser.add_argument(
        "--document",
        action="store_true",
        help="Force sending files as documents instead of photos.",
    )
    parser.add_argument(
        "--parse-mode",
        choices=("Markdown", "MarkdownV2", "HTML"),
        default=None,
        help="Optional Telegram parse mode for text/captions.",
    )
    args = parser.parse_args()

    token, chat_id = require_config()
    files = [Path(path).expanduser().resolve() for path in args.files]

    for path in files:
        if not path.exists():
            print(f"File not found: {path}", file=sys.stderr)
            return 1
        if not path.is_file():
            print(f"Not a file: {path}", file=sys.stderr)
            return 1

    if not args.message and not files:
        parser.error("Provide a message and/or at least one file.")

    try:
        if files:
            for index, path in enumerate(files):
                caption = args.message if index == 0 and args.message else None
                result = send_attachment(
                    token,
                    chat_id,
                    path,
                    caption,
                    args.parse_mode,
                    args.document,
                )
                if not result.get("ok"):
                    print(result, file=sys.stderr)
                    return 1
            if args.message and len(files) > 1:
                result = send_text(token, chat_id, args.message, args.parse_mode)
                if not result.get("ok"):
                    print(result, file=sys.stderr)
                    return 1
        elif args.message:
            result = send_text(token, chat_id, args.message, args.parse_mode)
            if not result.get("ok"):
                print(result, file=sys.stderr)
                return 1
    except requests.RequestException as exc:
        print(f"Telegram API error: {exc}", file=sys.stderr)
        return 1

    print("Sent to Telegram.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
