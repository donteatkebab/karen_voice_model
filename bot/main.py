from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from bot.config import load_config
from bot.database import Database
from bot.handlers.admin import router as admin_router
from bot.handlers.messages import router as messages_router
from bot.middlewares.context import ContextMiddleware
from bot.scheduler import build_scheduler


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    config = load_config()
    db = Database(config.database_path)
    bot = Bot(
        token=config.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()
    dp.update.outer_middleware(ContextMiddleware(db=db, config=config))
    dp.include_router(admin_router)
    dp.include_router(messages_router)

    scheduler = build_scheduler(bot, db, config)
    scheduler.start()

    try:
        await dp.start_polling(bot)
    finally:
        scheduler.shutdown(wait=False)
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
