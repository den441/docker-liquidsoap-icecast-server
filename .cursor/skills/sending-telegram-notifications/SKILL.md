---
name: sending-telegram-notifications
description: Sends and receives text, images, and documents through Telegram. Use when the user chats via Telegram, sends files through a TG bot, asks for TG delivery, or works in a Telegram agent dialog.
compatibility: Requires TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID for file download (in .env or Cloud Agent Secrets), network access, and python3 with requests.
---

# Telegram Agent Dialog

## Two different Telegram channels

### 1. Cursor Telegram bridge (how the user chats with you)

If the user says they are already talking to you through Telegram, that is Cursor's text bridge (for example cursor-tg or a similar connector). **Text messages reach the agent, but photos usually do not land on disk automatically.**

Do not tell the user to "create a new bot" unless file download is also failing after the steps below.

### 2. Project Telegram scripts (how the agent downloads files)

`telegram-receive.py` talks to the Telegram Bot API with `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID`. This can be the **same bot** the user already uses, as long as the token is available to the cloud agent.

Store credentials in:

- `/workspace/.env`, or
- Cursor Dashboard → Cloud Agents → Secrets (`TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`)

## First step when the user sent a photo in Telegram

Always run:

```bash
python3 scripts/telegram-input.py --wait --timeout 120 --ack
```

This tries to:

1. Download new files from the configured Telegram bot
2. Find images already saved under `assets/`, `input/telegram/`, or Cursor project assets

If nothing is found, explain that Cursor's Telegram text bridge does not automatically save photos, and suggest:

1. Send the image again as a **File/Document** (not a compressed Photo)
2. Send a direct `https://` image link
3. Add the bot token and chat id to Cloud Agent Secrets, then resend the photo to the same bot

## Receive files from the project bot

```bash
python3 scripts/telegram-receive.py --ack
python3 scripts/telegram-receive.py --wait --timeout 120 --ack
python3 scripts/telegram-receive.py --latest
python3 scripts/telegram-watch.py --ack
```

Files are saved to `input/telegram/` by default.

## Send messages and files back

```bash
python3 scripts/telegram-send.py "Готово." /path/to/result.png
```

## Diagnostics

```bash
python3 scripts/telegram-doctor.py
python3 scripts/telegram-input.py --json
```

## Agent behavior

- If the user says they sent a file in Telegram, run `telegram-input.py` before saying the file is missing.
- Do not confuse the Cursor text bridge with the project download scripts.
- After processing, send results with `telegram-send.py` when Telegram delivery is expected.
- Do not commit `.env` or expose tokens in chat, commits, or PRs.
