# Telegram AI Voice Group Member MVP

This project is a Telegram group member bot that only sends voice messages generated with Gemini Native Audio Dialog.

It is intentionally not a chatbot and does not send text replies.

## Features

- Owner-only group approval with `/approve`
- SQLite persistence
- Stores text messages only from approved groups
- Keeps only the latest 1000 messages per group
- Uses the last 50 messages as short-term memory
- Scheduled activity checks every 10 minutes
- Voice generation cooldown per group
- Sends only Telegram voice messages
- Docker and Railway ready

## Project Structure

```text
bot/
├── main.py
├── database.py
├── scheduler.py
├── handlers/
│   ├── admin.py
│   └── messages.py
├── services/
│   ├── memory.py
│   ├── trigger.py
│   └── voice.py
├── voice_model.py
├── models.py
├── config.py
└── requirements.txt
```

## Requirements

- Python 3.12+
- `ffmpeg`
- Telegram bot token
- Gemini API key
- Telegram owner user ID

## Environment Variables

Required:

- `BOT_TOKEN`
- `GEMINI_API_KEY`
- `OWNER_ID`

Optional:

- `DATABASE_PATH` default: `data/bot.sqlite3`
- `VOICE_COOLDOWN_MINUTES` default: `45`
- `TRIGGER_PROBABILITY` default: `0.2`
- `MIN_MESSAGES_FOR_ACTIVITY` default: `15`
- `TRIGGER_INTERVAL_MINUTES` default: `10`
- `RECENT_MEMORY_LIMIT` default: `50`
- `HISTORY_LIMIT_PER_GROUP` default: `1000`
- `ACTIVITY_WINDOW_MINUTES` default: `30`
- `GEMINI_AUDIO_MODEL` default: `gemini-3.1-flash-live-preview`
- `GEMINI_VOICE_NAME` default: `Kore`
- `GEMINI_API_VERSION` optional API version override

## Local Setup

1. Create and activate a virtual environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Copy `.env.example` to `.env` and fill in the required values.
4. Run the bot:

```bash
python -m bot.main
```

## How It Works

### Group approval

- The bot joins groups inactive.
- The owner sends `/approve` inside a group.
- The group is added to the `approved_groups` table.
- Only approved groups are processed.
- The owner can clear stored group data with `/clear_db`.
- The owner can revoke group approval with `/unapprove`.

### Message storage

- Only text messages from approved groups are stored.
- Media messages are ignored.
- Messages are trimmed to the most recent 1000 per group.

### Voice generation

- Every 10 minutes the scheduler checks each approved group.
- If a group had at least 8 messages in the last 30 minutes, the bot may speak.
- Default speaking probability is 35%.
- Voice output is generated from:
  - persona
  - recent 50 messages
  - reply or ambient instruction

### Reply modes

- 70%: reply to one recent message
- 30%: join the discussion naturally

### Cooldown

- A group can only receive a new voice message after the cooldown expires.
- Default cooldown is 45 minutes.

## Docker

Build:

```bash
docker build -t telegram-voice-bot .
```

Run:

```bash
docker run --rm \
  -e BOT_TOKEN="$BOT_TOKEN" \
  -e GEMINI_API_KEY="$GEMINI_API_KEY" \
  -e OWNER_ID="$OWNER_ID" \
  telegram-voice-bot
```

## Railway

This repo includes:

- `Dockerfile`
- `railway.json`

Deploy it as a Docker-based Railway service and set the required environment variables in the Railway dashboard.

## Notes

- The bot never sends text responses during normal operation.
- The bot does not use embeddings, vector search, long-term memory, or user profiling.
- The voice generation wrapper lives in `voice_model.py` and is reused by the bot package.

