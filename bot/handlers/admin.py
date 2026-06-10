from __future__ import annotations

from datetime import datetime, timezone

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import BufferedInputFile, Message

from bot.config import Config
from bot.database import Database
from bot.services.memory import get_recent_group_messages
from bot.models import StoredMessage
from bot.services.pronunciation import (
    add_pronunciation_rule,
    remove_pronunciation_rule,
)
from bot.services.voice import generate_group_voice

router = Router(name="admin")


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )


def _to_stored_message(message: Message) -> StoredMessage | None:
    if not message.from_user:
        return None
    username = message.from_user.username or message.from_user.full_name or str(
        message.from_user.id
    )
    return StoredMessage(
        id=0,
        group_id=message.chat.id,
        telegram_message_id=message.message_id,
        user_id=message.from_user.id,
        username=username,
        text=(message.text or "").strip(),
        created_at=_utc_now_iso(),
    )


def _describe_owner_reply(
    *, owner_message: Message, reply_to: Message | None
) -> str:
    if reply_to is None:
        return "Owner sent the trigger text without replying to a specific message."
    if reply_to.from_user and owner_message.from_user and reply_to.from_user.id == owner_message.from_user.id:
        return "Owner sent the trigger text as a reply to their own message."
    return "Owner sent the trigger text as a reply to another user's message."


def _extract_owner_request(message: Message) -> str | None:
    text = (message.text or "").strip()
    if not text:
        return None
    parts = text.split(maxsplit=1)
    if len(parts) < 2:
        return None
    request = parts[1].strip()
    return request or None


@router.message(Command("approve"))
async def approve_group(message: Message, db: Database, config: Config) -> None:
    if not message.from_user or message.from_user.id != config.owner_id:
        return

    if message.chat.type not in {"group", "supergroup"}:
        await message.answer("This command only works in a group.")
        return

    title = message.chat.title or "Unnamed group"
    db.approve_group(message.chat.id, title, _utc_now_iso())
    await message.answer("Group approved.")


@router.message(Command("unapprove"))
async def unapprove_group(message: Message, db: Database, config: Config) -> None:
    if not message.from_user or message.from_user.id != config.owner_id:
        return

    if message.chat.type not in {"group", "supergroup"}:
        await message.answer("این دستور فقط در گروه یا سوپرگروه کار می‌کند.")
        return

    if not db.is_group_approved(message.chat.id):
        await message.answer("این گروه از قبل تأیید نشده است.")
        return

    db.unapprove_group(message.chat.id)
    await message.answer("گروه دیگر تأییدشده نیست و در بررسی‌های بعدی پردازش نخواهد شد.")


@router.message(Command("test_voice"))
async def test_voice(message: Message, db: Database, config: Config) -> None:
    if not message.from_user or message.from_user.id != config.owner_id:
        return

    if message.chat.type not in {"group", "supergroup"}:
        return

    if not db.is_group_approved(message.chat.id):
        return

    recent_messages = get_recent_group_messages(
        db, message.chat.id, limit=config.recent_memory_limit
    )
    audio_bytes = await generate_group_voice(
        config=config,
        recent_messages=recent_messages,
        instruction=config.test_voice_instruction,
    )
    voice = BufferedInputFile(audio_bytes, filename="test_voice.ogg")
    await message.answer_voice(voice=voice, reply_to_message_id=message.message_id)


@router.message(Command("pron"))
async def pronounce_command(message: Message, config: Config) -> None:
    if not message.from_user or message.from_user.id != config.owner_id:
        return

    if not message.text:
        return

    raw_args = message.text.split(maxsplit=1)
    if len(raw_args) < 2 or not raw_args[1].strip():
        await message.answer(
            "فرمت:\n"
            "/pron <قاعده تلفظ>\n"
            "/pron remove <قاعده تلفظ>\n"
            "مثال:\n"
            "/pron به جای گه بگو گوه"
        )
        return

    args = raw_args[1].strip()

    if args.startswith("remove "):
        rule = args[len("remove ") :].strip()
        if not rule:
            await message.answer("فرمت حذف:\n/pron remove <قاعده تلفظ>")
            return
        remove_pronunciation_rule(rule)
        await message.answer(f"حذف شد:\n{rule}")
        return

    add_pronunciation_rule(args)
    await message.answer(f"ثبت شد:\n{args}")


@router.message(Command("karen"))
async def owner_karan_trigger(message: Message, db: Database, config: Config) -> None:
    if not message.from_user or message.from_user.id != config.owner_id:
        return

    if message.chat.type not in {"group", "supergroup"}:
        return

    if not db.is_group_approved(message.chat.id):
        return

    recent_messages = get_recent_group_messages(
        db, message.chat.id, limit=config.recent_memory_limit
    )
    reply_to = message.reply_to_message
    selected_message = None
    if reply_to and reply_to.text:
        stored_reply = db.get_message_by_telegram_id(message.chat.id, reply_to.message_id)
        selected_message = stored_reply or _to_stored_message(reply_to)

    trigger_context = _describe_owner_reply(owner_message=message, reply_to=reply_to)
    owner_request = _extract_owner_request(message)
    instruction = config.karen_instruction

    audio_bytes = await generate_group_voice(
        config=config,
        recent_messages=recent_messages,
        instruction=instruction,
        selected_message=selected_message,
        trigger_context=trigger_context,
        owner_request=owner_request,
    )
    voice = BufferedInputFile(audio_bytes, filename="karen_trigger.ogg")
    await message.answer_voice(voice=voice, reply_to_message_id=message.message_id)


@router.message(Command("clear_db"))
async def clear_group_database(message: Message, db: Database, config: Config) -> None:
    if not message.from_user or message.from_user.id != config.owner_id:
        return

    if message.chat.type not in {"group", "supergroup"}:
        await message.answer("این دستور فقط در گروه یا سوپرگروه کار می‌کند.")
        return

    if not db.is_group_approved(message.chat.id):
        await message.answer("این گروه مورد تأیید نیست.")
        return

    db.clear_group_data(message.chat.id)
    await message.answer(
        "دیتابیس ذخیره‌شده برای این گروه پاک شد. پیام‌ها و وضعیت آخرین ویس حذف شدند."
    )
