from __future__ import annotations

from datetime import datetime, timezone

from aiogram import F, Router
from aiogram.types import Message

from bot.config import Config
from bot.database import Database

router = Router(name="messages")


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )


@router.message(F.chat.type.in_({"group", "supergroup"}), F.text, ~F.text.startswith("/"))
async def store_group_text_message(message: Message, db: Database, config: Config) -> None:
    if not message.from_user:
        return

    if message.from_user.is_bot:
        return

    if not db.is_group_approved(message.chat.id):
        return

    text = (message.text or "").strip()
    if not text:
        return

    username = message.from_user.username or message.from_user.full_name or str(
        message.from_user.id
    )
    db.add_message(
        group_id=message.chat.id,
        telegram_message_id=message.message_id,
        user_id=message.from_user.id,
        username=username,
        text=text,
        created_at=_utc_now_iso(),
        history_limit=config.history_limit_per_group,
    )
