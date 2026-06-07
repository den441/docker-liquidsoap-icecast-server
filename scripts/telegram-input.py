#!/usr/bin/env python3
"""Find or download user files sent through Telegram."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import requests

from telegram_config import load_env, workspace_root
from telegram_receive import DEFAULT_INPUT_DIR, latest_downloaded_file, receive_new_items

IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".tif", ".tiff"}


def cursor_attachment_dirs() -> list[Path]:
    root = workspace_root()
    candidates = [
        root / "assets",
        root / "input",
        root / "input" / "telegram",
        root / ".cursor" / "projects" / "workspace" / "assets",
        Path("/opt/cursor/artifacts/assets"),
    ]
    projects = root / ".cursor" / "projects"
    if projects.exists():
        candidates.extend(projects.glob("*/assets"))
    return [path for path in candidates if path.exists()]


def find_local_attachments() -> list[Path]:
    found: list[Path] = []
    for directory in cursor_attachment_dirs():
        for path in directory.rglob("*"):
            if not path.is_file():
                continue
            if path.name.endswith(".meta.json"):
                continue
            if path.suffix.lower() in IMAGE_SUFFIXES.union({".pdf", ".zip", ".txt"}):
                found.append(path.resolve())
    return sorted(found, key=lambda item: item.stat().st_mtime, reverse=True)


def has_telegram_config() -> bool:
    return bool(
        os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
        and os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    )


def main() -> int:
    load_env()
    parser = argparse.ArgumentParser(
        description="Locate or download files the user sent via Telegram."
    )
    parser.add_argument(
        "--wait",
        action="store_true",
        help="Wait for a new Telegram file when bot credentials are configured.",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=120,
        help="Long-poll timeout for --wait (default: 120).",
    )
    parser.add_argument(
        "--ack",
        action="store_true",
        help="Confirm receipt in Telegram after download.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print results as JSON.",
    )
    args = parser.parse_args()

    results: list[dict[str, object]] = []

    if has_telegram_config():
        try:
            items = receive_new_items(
                wait_timeout=args.timeout if args.wait else 0,
                ack=args.ack,
            )
            for item in items:
                if item.path:
                    results.append(
                        {
                            "source": "telegram-bot",
                            "path": str(item.path),
                            "kind": item.kind,
                            "caption": item.caption,
                            "text": item.text,
                        }
                    )
        except (requests.RequestException, RuntimeError) as exc:
            print(f"Telegram download failed: {exc}", file=sys.stderr)

    for path in find_local_attachments():
        results.append({"source": "workspace", "path": str(path), "kind": path.suffix.lower()})

    if not results:
        latest = latest_downloaded_file(DEFAULT_INPUT_DIR)
        if latest:
            results.append({"source": "telegram-cache", "path": str(latest), "kind": latest.suffix.lower()})

    if not results:
        if args.json:
            print(json.dumps({"items": [], "configured": has_telegram_config()}, ensure_ascii=False))
        else:
            print("No Telegram files found in the workspace.", file=sys.stderr)
            print(file=sys.stderr)
            print(
                "If you chat with the agent through Telegram, text arrives via Cursor's bridge, "
                "but photos are often not saved automatically.",
                file=sys.stderr,
            )
            print("Try one of these:", file=sys.stderr)
            print("  1. Send the image as a File/Document, not a compressed Photo.", file=sys.stderr)
            print("  2. Send a direct https:// link to the image.", file=sys.stderr)
            print(
                "  3. Add TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID to Cloud Agent Secrets, "
                "then send the photo to the same bot again.",
                file=sys.stderr,
            )
        return 1

    if args.json:
        print(json.dumps({"items": results, "configured": has_telegram_config()}, ensure_ascii=False))
    else:
        for item in results:
            print(item["path"])

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
