#!/usr/bin/env python3
"""Continuously receive files sent to the Telegram bot."""

from __future__ import annotations

import argparse
import sys
import time

import requests

from telegram_config import load_env
from telegram_receive import DEFAULT_INPUT_DIR, receive_new_items


def main() -> int:
    load_env()
    parser = argparse.ArgumentParser(
        description="Keep polling Telegram and save incoming files automatically."
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=30,
        help="Long-poll timeout in seconds (default: 30).",
    )
    parser.add_argument(
        "--ack",
        action="store_true",
        help="Reply in Telegram when a file is received.",
    )
    args = parser.parse_args()

    print("Telegram watch started. Send a photo or file to your bot.")
    print(f"Saving to: {DEFAULT_INPUT_DIR}")
    print("Press Ctrl+C to stop.")

    while True:
        try:
            items = receive_new_items(
                wait_timeout=args.timeout,
                ack=args.ack,
            )
        except requests.RequestException as exc:
            print(f"Telegram API error: {exc}", file=sys.stderr)
            time.sleep(5)
            continue
        except RuntimeError as exc:
            print(exc, file=sys.stderr)
            return 1

        for item in items:
            if item.path:
                print(f"received {item.kind}: {item.path}")
            elif item.text or item.caption:
                print(f"received text: {item.text or item.caption}")


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\nStopped.")
        raise SystemExit(0)
