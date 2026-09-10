from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from bot.db.crud import get_or_create_user
from bot.db.session import SessionFactory
from bot.keyboards.main_menu import main_menu

router = Router()


@router.message(CommandStart())
async def start(message: Message) -> None:
    async with SessionFactory() as session:
        user = await get_or_create_user(session, message.from_user.id, message.from_user.username)
    await message.answer("Добро пожаловать в Q1 GPT! Выберите действие:", reply_markup=main_menu())
