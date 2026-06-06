from __future__ import annotations

from bot.config import Config
from bot.models import StoredMessage
from bot.services.memory import build_prompt
from bot.voice_model import generate_voice_ogg_bytes


async def generate_group_voice(
    *,
    config: Config,
    recent_messages: list[StoredMessage],
    instruction: str,
    selected_message: StoredMessage | None = None,
    trigger_context: str | None = None,
    owner_request: str | None = None,
) -> bytes:
    prompt = build_prompt(
        recent_messages=recent_messages,
        instruction=instruction,
        selected_message=selected_message,
        trigger_context=trigger_context,
        owner_request=owner_request,
    )
    return await generate_voice_ogg_bytes(
        prompt=prompt,
        api_key=config.gemini_api_key,
        model=config.gemini_model,
        voice_name=config.gemini_voice_name,
        api_version=config.gemini_api_version or None,
    )
