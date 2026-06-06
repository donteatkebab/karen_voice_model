from __future__ import annotations

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from aiogram import Bot

from bot.config import Config
from bot.database import Database
from bot.services.trigger import check_group_activity


def build_scheduler(bot: Bot, db: Database, config: Config) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone="UTC")
    scheduler.add_job(
        check_group_activity,
        "interval",
        minutes=config.trigger_interval_minutes,
        args=[bot, db, config],
        id="group_activity_check",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    return scheduler

