from __future__ import annotations

import logging
import random
from datetime import datetime, timedelta, timezone

from aiogram import Bot
from aiogram.types import BufferedInputFile

from bot.config import Config
from bot.database import Database
from bot.models import StoredMessage
from bot.services.voice import generate_group_voice

logger = logging.getLogger(__name__)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )


def _parse_iso(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


async def maybe_send_voice_for_group(
    *,
    bot: Bot,
    db: Database,
    config: Config,
    group_id: int,
) -> bool:
    now = datetime.now(timezone.utc)
    last_voice_at = db.get_last_voice_at(group_id)
    if last_voice_at is not None:
        delta = now - _parse_iso(last_voice_at)
        if delta < timedelta(minutes=config.voice_cooldown_minutes):
            return False

    if random.random() > config.trigger_probability:
        return False

    recent_messages = db.get_recent_messages(group_id, limit=config.recent_memory_limit)
    if not recent_messages:
        return False

    mode_reply = random.random() < 0.7
    selected_message: StoredMessage | None = None
    instruction = config.instruction_join
    reply_message_id: int | None = None

    if mode_reply:
        selected_message = random.choice(recent_messages)
        instruction = config.instruction_reply
        reply_message_id = selected_message.telegram_message_id

    try:
        audio_bytes = await generate_group_voice(
            config=config,
            recent_messages=recent_messages,
            instruction=instruction,
            selected_message=selected_message,
        )
        if not audio_bytes:
            return False

        voice = BufferedInputFile(audio_bytes, filename="voice.ogg")
        send_kwargs = {"chat_id": group_id, "voice": voice}
        if reply_message_id is not None:
            send_kwargs["reply_to_message_id"] = reply_message_id

        await bot.send_voice(**send_kwargs)
        db.set_last_voice_at(group_id, _utc_now_iso())
        return True
    except Exception:
        logger.exception("Failed to generate or send voice for group %s", group_id)
        return False


async def check_group_activity(bot: Bot, db: Database, config: Config) -> None:
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=config.activity_window_minutes)
    cutoff_iso = cutoff.replace(microsecond=0).isoformat().replace("+00:00", "Z")
    approved_groups = db.list_approved_groups()
    for group in approved_groups:
        try:
            activity_count = db.count_messages_since(group.group_id, cutoff_iso)
            if activity_count < config.min_messages_for_activity:
                continue
            await maybe_send_voice_for_group(
                bot=bot,
                db=db,
                config=config,
                group_id=group.group_id,
            )
        except Exception:
            logger.exception("Activity check failed for group %s", group.group_id)
