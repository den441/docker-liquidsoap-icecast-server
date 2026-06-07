"""Shared Telegram bot configuration helpers."""

from __future__ import annotations

import os
import sys
from pathlib import Path


def load_env() -> None:
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def require_config() -> tuple[str, str]:
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    missing = []
    if not token:
        missing.append("TELEGRAM_BOT_TOKEN")
    if not chat_id:
        missing.append("TELEGRAM_CHAT_ID")
    if missing:
        print(
            "Missing Telegram config: "
            + ", ".join(missing)
            + "\nCopy .env.example to .env and fill in values. "
            "Run `python3 scripts/telegram-setup.py` to discover chat id.",
            file=sys.stderr,
        )
        sys.exit(1)
    return token, chat_id
