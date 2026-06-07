#!/usr/bin/env python3
"""Discover Telegram chat id after the user sends /start to the bot."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import requests

from telegram_config import load_env


def main() -> int:
    load_env()
    load_env()
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        print(
            "Set TELEGRAM_BOT_TOKEN in .env first.\n"
            "1. Open @BotFather in Telegram and create a bot.\n"
            "2. Copy the token into .env.\n"
            "3. Send /start to your bot from the account that should receive messages.\n"
            "4. Run this script again.",
            file=sys.stderr,
        )
        return 1

    response = requests.get(
        f"https://api.telegram.org/bot{token}/getUpdates",
        timeout=30,
    )
    response.raise_for_status()
    payload = response.json()
    if not payload.get("ok"):
        print(payload, file=sys.stderr)
        return 1

    updates = payload.get("result", [])
    if not updates:
        print(
            "No messages found. Send /start to your bot in Telegram, then rerun this script.",
            file=sys.stderr,
        )
        return 1

    latest = updates[-1]
    message = latest.get("message") or latest.get("channel_post") or {}
    chat = message.get("chat") or {}
    chat_id = chat.get("id")
    if chat_id is None:
        print("Could not read chat id from Telegram updates.", file=sys.stderr)
        return 1

    env_path = Path(__file__).resolve().parent.parent / ".env"
    chat_id_str = str(chat_id)
    title = chat.get("title") or chat.get("username") or chat.get("first_name") or "chat"

    if env_path.exists():
        lines = env_path.read_text(encoding="utf-8").splitlines()
        replaced = False
        new_lines = []
        for line in lines:
            if line.startswith("TELEGRAM_CHAT_ID="):
                new_lines.append(f"TELEGRAM_CHAT_ID={chat_id_str}")
                replaced = True
            else:
                new_lines.append(line)
        if not replaced:
            new_lines.append(f"TELEGRAM_CHAT_ID={chat_id_str}")
        env_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
    else:
        env_path.write_text(
            f"TELEGRAM_BOT_TOKEN={os.environ.get('TELEGRAM_BOT_TOKEN', '')}\n"
            f"TELEGRAM_CHAT_ID={chat_id_str}\n",
            encoding="utf-8",
        )

    print(f"Saved TELEGRAM_CHAT_ID={chat_id_str} for {title}.")
    print("Test with: python3 scripts/telegram-send.py 'Telegram is connected.'")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
