---
name: sending-telegram-notifications
description: Sends text, images, and documents to the user through a configured Telegram bot. Use when the user asks to notify them in Telegram, send files or screenshots to Telegram, deliver results via TG bot, or when finishing work and Telegram delivery was requested.
compatibility: Requires TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in .env, network access, and python3 with requests.
---

# Sending Telegram Notifications

Use this skill when the user wants messages or attachments delivered to Telegram.

## Before sending

1. Ensure `/workspace/.env` exists with:
   - `TELEGRAM_BOT_TOKEN`
   - `TELEGRAM_CHAT_ID`
2. If credentials are missing, tell the user to:
   - create a bot via [@BotFather](https://t.me/BotFather)
   - copy `.env.example` to `.env` and paste the token
   - send `/start` to the bot from their Telegram account
   - run `python3 scripts/telegram-setup.py` to save chat id
3. Do not commit `.env` or expose tokens in chat, commits, or PRs.

## Send commands

Text only:

```bash
python3 scripts/telegram-send.py "Task finished. Ready for review."
```

Text with one or more attachments:

```bash
python3 scripts/telegram-send.py "Logo attached." /path/to/file.png
python3 scripts/telegram-send.py "Docs attached." report.pdf data.csv
```

Force documents instead of photos:

```bash
python3 scripts/telegram-send.py "Archive attached." --document archive.zip
```

Optional formatting:

```bash
python3 scripts/telegram-send.py "**Done**" --parse-mode Markdown
```

## Agent behavior

- Prefer Telegram when the user explicitly asks for TG delivery or ongoing Telegram updates.
- Attach generated images, exported files, logs, or reports when they are part of the deliverable.
- Keep Telegram messages concise; put long details in attached documents when needed.
- After sending, confirm in chat that the Telegram message was delivered.
- If sending fails, report the API error and ask the user to verify `.env` values.
