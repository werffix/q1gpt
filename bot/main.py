import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from bot.config import get_settings
from bot.db.crud import seed_models
from bot.db.session import SessionFactory, init_db
from bot.handlers import admin, chat, inline, model_select, my_chats, start
from bot.middlewares.access import AccessMiddleware


async def main() -> None:
    settings = get_settings()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s", handlers=[logging.StreamHandler(), logging.FileHandler("bot.log")])
    await init_db()
    async with SessionFactory() as session:
        await seed_models(session)
    bot = Bot(settings.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dispatcher = Dispatcher()
    dispatcher.message.middleware(AccessMiddleware())
    dispatcher.callback_query.middleware(AccessMiddleware())
    dispatcher.inline_query.middleware(AccessMiddleware())
    dispatcher.include_routers(start.router, model_select.router, my_chats.router, admin.router, chat.router, inline.router)
    await bot.delete_webhook(drop_pending_updates=True)
    await dispatcher.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        sys.exit(0)
