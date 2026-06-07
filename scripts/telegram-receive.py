#!/usr/bin/env python3
"""Receive files and messages sent to the Telegram bot by the configured user."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import requests

from telegram_config import load_env
from telegram_receive import DEFAULT_INPUT_DIR, latest_downloaded_file, receive_new_items


def main() -> int:
    load_env()
    parser = argparse.ArgumentParser(
        description="Download new files and messages from the Telegram bot dialog."
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=DEFAULT_INPUT_DIR,
        help=f"Directory for downloaded files (default: {DEFAULT_INPUT_DIR})",
    )
    parser.add_argument(
        "--wait",
        action="store_true",
        help="Long-poll Telegram until a message arrives.",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=120,
        help="Long-poll timeout in seconds when --wait is used (default: 120).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List pending updates without downloading or advancing offset.",
    )
    parser.add_argument(
        "--ack",
        action="store_true",
        help="Send a short confirmation message after files are received.",
    )
    parser.add_argument(
        "--latest",
        action="store_true",
        help="Print the most recently downloaded file path and exit.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print received items as JSON lines.",
    )
    args = parser.parse_args()

    if args.latest:
        latest = latest_downloaded_file(args.output)
        if latest is None:
            print("No downloaded files yet.", file=sys.stderr)
            return 1
        print(latest)
        return 0

    try:
        items = receive_new_items(
            args.output,
            wait_timeout=args.timeout if args.wait else 0,
            dry_run=args.dry_run,
            ack=args.ack,
        )
    except requests.RequestException as exc:
        print(f"Telegram API error: {exc}", file=sys.stderr)
        return 1
    except RuntimeError as exc:
        print(exc, file=sys.stderr)
        return 1

    if not items:
        if args.wait:
            print("No new Telegram messages before timeout.", file=sys.stderr)
        else:
            print("No new Telegram messages.")
        return 0

    if args.json:
        for item in items:
            payload = {
                "update_id": item.update_id,
                "message_id": item.message_id,
                "kind": item.kind,
                "path": str(item.path) if item.path else None,
                "text": item.text,
                "caption": item.caption,
                "received_at": item.received_at,
            }
            print(json.dumps(payload, ensure_ascii=False))
    else:
        for item in items:
            if item.path:
                print(item.path)
            elif item.text or item.caption:
                print(item.text or item.caption)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
