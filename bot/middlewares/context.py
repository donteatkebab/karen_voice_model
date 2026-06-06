from __future__ import annotations

from aiogram.dispatcher.middlewares.base import BaseMiddleware


class ContextMiddleware(BaseMiddleware):
    def __init__(self, *, db, config) -> None:
        self._db = db
        self._config = config

    async def __call__(self, handler, event, data):
        data["db"] = self._db
        data["config"] = self._config
        return await handler(event, data)

