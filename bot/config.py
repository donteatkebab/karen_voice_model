from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


PERSONA_PATH = Path(__file__).with_name("persona.txt")
VOICE_STYLE_PATH = Path(__file__).with_name("voice_style.txt")


def load_persona() -> str:
    return PERSONA_PATH.read_text(encoding="utf-8").strip()


def load_voice_style() -> str:
    return VOICE_STYLE_PATH.read_text(encoding="utf-8").strip()


@dataclass(frozen=True, slots=True)
class Config:
    bot_token: str
    gemini_api_key: str
    owner_id: int
    database_path: str
    voice_cooldown_minutes: int = 1
    trigger_probability: float = 0.5
    min_messages_for_activity: int = 8
    trigger_interval_minutes: int = 5
    recent_memory_limit: int = 50
    history_limit_per_group: int = 1000
    activity_window_minutes: int = 30
    gemini_model: str = "gemini-3.1-flash-live-preview"
    gemini_voice_name: str = "Achernar"
    gemini_api_version: str = ""
    # Instruction templates (editable defaults)
    instruction_join: str = "بر اساس محتوای چت یه چیز بگو"
    instruction_reply: str = "به پیام مورد نظر پاسخ بده."
    test_voice_instruction: str = "همینجوری یه چیز رندوم بگو"
    karen_instruction: str = (
        "بر اساس سوال کاربر به سوال پاسخ بده اگه نیاز بود از حافظه چت هم استفاده کن."
        "اگر owner روی پیام کسی reply زده، همان پیام را مبنا قرار بده. "
        "اگر owner روی پیام خودش reply زده، ادامه همان رشته گفتگو را طبیعی پاسخ بده. "
        "اگر owner بعد از /karen متن هم نوشته، همان درخواست را هم اجرا کن. "
    )


def _required(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def load_config() -> Config:
    load_dotenv()
    base_dir = Path(os.getenv("DATABASE_PATH", "data/bot.sqlite3"))
    return Config(
        bot_token=_required("BOT_TOKEN"),
        gemini_api_key=_required("GEMINI_API_KEY"),
        owner_id=int(_required("OWNER_ID")),
        database_path=str(base_dir),
        voice_cooldown_minutes=int(os.getenv("VOICE_COOLDOWN_MINUTES", "45")),
        trigger_probability=float(os.getenv("TRIGGER_PROBABILITY", "0.2")),
        min_messages_for_activity=int(os.getenv("MIN_MESSAGES_FOR_ACTIVITY", "15")),
        trigger_interval_minutes=int(os.getenv("TRIGGER_INTERVAL_MINUTES", "10")),
        recent_memory_limit=int(os.getenv("RECENT_MEMORY_LIMIT", "50")),
        history_limit_per_group=int(os.getenv("HISTORY_LIMIT_PER_GROUP", "1000")),
        activity_window_minutes=int(os.getenv("ACTIVITY_WINDOW_MINUTES", "30")),
        gemini_model=os.getenv(
            "GEMINI_AUDIO_MODEL", "gemini-2.5-flash-native-audio-preview-12-2025"
        ),
        gemini_voice_name=os.getenv("GEMINI_VOICE_NAME", "Achernar"),
        gemini_api_version=os.getenv("GEMINI_API_VERSION", ""),
    )
