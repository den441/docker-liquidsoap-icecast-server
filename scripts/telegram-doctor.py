#!/usr/bin/env python3
"""Check Telegram bot configuration and pending messages."""

from __future__ import annotations

import os
import sys

import requests

from telegram_config import load_env, workspace_root
from telegram_receive import DEFAULT_INPUT_DIR, api_base, fetch_updates


def main() -> int:
    load_env()
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    env_path = workspace_root() / ".env"

    print("Telegram diagnostics")
    print("------------------")
    print(f".env file: {'found' if env_path.exists() else 'MISSING'} ({env_path})")
    print(f"TELEGRAM_BOT_TOKEN: {'set' if token else 'MISSING'}")
    print(f"TELEGRAM_CHAT_ID: {chat_id or 'MISSING'}")
    print(f"Download dir: {DEFAULT_INPUT_DIR}")

    if not token:
        print()
        print("Fix:")
        print("1. cp .env.example .env")
        print("2. Paste bot token from @BotFather into TELEGRAM_BOT_TOKEN")
        print("3. Send /start to your bot in Telegram")
        print("4. python3 scripts/telegram-setup.py")
        return 1

    try:
        response = requests.get(f"{api_base(token)}/getMe", timeout=30)
        response.raise_for_status()
        me = response.json()
    except requests.RequestException as exc:
        print(f"getMe failed: {exc}")
        return 1

    if not me.get("ok"):
        print(f"getMe error: {me}")
        return 1

    bot = me["result"]
    print(f"Bot: @{bot.get('username')} ({bot.get('first_name')})")

    try:
        updates = fetch_updates(token, offset=None, timeout=0)
    except requests.RequestException as exc:
        print(f"getUpdates failed: {exc}")
        return 1

    print(f"Pending updates in Telegram queue: {len(updates)}")

    if not chat_id:
        print()
        print("TELEGRAM_CHAT_ID is missing.")
        if updates:
            latest = updates[-1]
            message = latest.get("message") or latest.get("edited_message") or {}
            found_chat = (message.get("chat") or {}).get("id")
            if found_chat is not None:
                print(f"Latest message chat id: {found_chat}")
                print("Run: python3 scripts/telegram-setup.py")
        else:
            print("Send /start to your bot, then run: python3 scripts/telegram-setup.py")
        return 1

    matched = 0
    for update in updates:
        message = update.get("message") or update.get("edited_message")
        if not message:
            continue
        if str((message.get("chat") or {}).get("id")) == str(chat_id):
            matched += 1
            kind = "text"
            if message.get("photo"):
                kind = "photo"
            elif message.get("document"):
                kind = "document"
            print(f"  - update {update['update_id']}: {kind}")

    print(f"Pending updates from your chat: {matched}")

    if matched:
        print()
        print("Download them with:")
        print("  python3 scripts/telegram-receive.py --ack")
    else:
        print()
        print("No pending files yet. Send a photo to the bot, then run:")
        print("  python3 scripts/telegram-watch.py")
        print("or")
        print("  python3 scripts/telegram-receive.py --wait --ack")

    return 0 if token and chat_id else 1


if __name__ == "__main__":
    raise SystemExit(main())
