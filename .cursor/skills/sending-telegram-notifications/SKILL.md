---
name: sending-telegram-notifications
description: Sends and receives text, images, and documents through a configured Telegram bot. Use when the user asks to notify them in Telegram, send or receive files via TG bot, work with a Telegram agent dialog, or deliver results through Telegram.
compatibility: Requires TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in .env, network access, and python3 with requests.
---

# Telegram Agent Dialog

Use this skill when the user interacts with the project through a Telegram bot: send results, or receive photos/files/instructions from the user.

## Before using Telegram

1. Ensure `/workspace/.env` exists with:
   - `TELEGRAM_BOT_TOKEN`
   - `TELEGRAM_CHAT_ID`
2. If credentials are missing, tell the user to:
   - create a bot via [@BotFather](https://t.me/BotFather)
   - copy `.env.example` to `.env` and paste the token
   - send `/start` to the bot from their Telegram account
   - run `python3 scripts/telegram-setup.py` to save chat id
3. Do not commit `.env` or expose tokens in chat, commits, or PRs.

## Receive files from the user

When the user sends a photo, document, or text to the bot and asks the agent to process it:

```bash
# Download everything new since the last run
python3 scripts/telegram-receive.py

# Wait up to 2 minutes for a new message from the user
python3 scripts/telegram-receive.py --wait --timeout 120 --ack

# Show pending updates without downloading
python3 scripts/telegram-receive.py --dry-run

# Get the latest downloaded file path
python3 scripts/telegram-receive.py --latest
```

Files are saved to `input/telegram/` by default. Each file has a `.meta.json` sidecar with caption and message text.

Agent workflow for tasks like photo editing:

1. Ask the user to send the file to the Telegram bot if it is not in the workspace yet.
2. Run `python3 scripts/telegram-receive.py --wait --timeout 120 --ack`.
3. Use the printed file path as input for processing.
4. Send the result back with `telegram-send.py`.

Only messages from `TELEGRAM_CHAT_ID` are accepted.

## Send messages and files

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

## Troubleshooting

If the user sent a file but nothing happened:

```bash
python3 scripts/telegram-doctor.py
```

Common causes:

1. `.env` is missing or incomplete — the bot cannot connect without `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID`.
2. Nothing is polling Telegram automatically — run `telegram-receive.py` or start `telegram-watch.py`.
3. The message came from another Telegram account — only `TELEGRAM_CHAT_ID` is accepted.

After fixing `.env`, download pending files with:

```bash
python3 scripts/telegram-receive.py --ack
```

For continuous receiving while working:

```bash
python3 scripts/telegram-watch.py --ack
```

## Agent behavior

- If the user says they sent a file in Telegram, run `telegram-doctor.py`, then `telegram-receive.py --ack`.
- If the user refers to a file sent in Telegram, run `telegram-receive.py` before saying the file is missing.
- Prefer Telegram when the user explicitly asks for TG delivery or ongoing Telegram updates.
- Attach generated images, exported files, logs, or reports when they are part of the deliverable.
- Keep Telegram messages concise; put long details in attached documents when needed.
- After sending, confirm in chat that the Telegram message was delivered.
- If sending fails, report the API error and ask the user to verify `.env` values.
