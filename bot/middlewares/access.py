from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, InlineQuery, Message, TelegramObject

from bot.config import get_settings
from bot.db.crud import is_allowed, log_access_attempt
from bot.db.session import SessionFactory


class AccessMiddleware(BaseMiddleware):
    async def __call__(self, handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]], event: TelegramObject, data: dict[str, Any]) -> Any:
        user = getattr(event, "from_user", None)
        if not user:
            return await handler(event, data)
        settings = get_settings()
        if user.id in settings.admin_id_set:
            return await handler(event, data)
        async with SessionFactory() as session:
            allowed = await is_allowed(session, user.id, user.username)
            if allowed:
                return await handler(event, data)
            await log_access_attempt(session, user.id, user.username)
        if isinstance(event, Message):
            await event.answer("⛔ У вас нет доступа к этому боту")
        elif isinstance(event, CallbackQuery):
            await event.answer("⛔ Нет доступа", show_alert=True)
        elif isinstance(event, InlineQuery):
            await event.answer([], cache_time=0, is_personal=True)
        return None
