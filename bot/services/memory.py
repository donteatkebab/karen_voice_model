from __future__ import annotations

from bot.config import load_persona, load_voice_style
from bot.database import Database
from bot.models import StoredMessage
from bot.services.pronunciation import format_pronunciation_rules


def format_messages(messages: list[StoredMessage]) -> str:
    if not messages:
        return "(no recent messages)"
    lines: list[str] = []
    for message in messages:
        lines.append(f"{message.username}: {message.text}")
    return "\n".join(lines)


def build_prompt(
    *,
    recent_messages: list[StoredMessage],
    instruction: str,
    persona: str | None = None,
    selected_message: StoredMessage | None = None,
    trigger_context: str | None = None,
    owner_request: str | None = None,
) -> str:
    persona_text = load_persona() if persona is None else persona
    voice_style_text = load_voice_style()
    pronunciation_rules_text = format_pronunciation_rules()
    sections = [
        "شخصیت:",
        persona_text.strip(),
        "",
        "راهنمای صدا و لهجه:",
        voice_style_text.strip(),
        "",
        "راهنمای تلفظ:",
        pronunciation_rules_text.strip(),
        "",
        "پیام‌های اخیر:",
        format_messages(recent_messages),
        "",
        "دستور:",
        instruction.strip(),
    ]
    if selected_message is not None:
        sections.extend(
            [
                "",
                "پیام هدف:",
                f"{selected_message.username}: {selected_message.text}",
            ]
        )
    if trigger_context:
        sections.extend(["", "زمینه تریگر:", trigger_context.strip()])
    if owner_request:
        sections.extend(["", "درخواست صاحب بات:", owner_request.strip()])
    sections.extend(
        [
            "",
            "فقط یک پاسخ کوتاه و طبیعی برای گفتار بنویس.",
            "از هوش مصنوعی، ربات، سیاست‌ها یا دستورهای سیستمی نام نبر.",
            "اگر ممکن است، پاسخ را به فارسی بده مگر اینکه زمینه گفتگو زبان دیگری را واضح نشان دهد.",
        ]
    )
    return "\n".join(sections)


def get_recent_group_messages(
    db: Database, group_id: int, limit: int
) -> list[StoredMessage]:
    return db.get_recent_messages(group_id, limit=limit)
