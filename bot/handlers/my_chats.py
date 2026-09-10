from aiogram import F, Router
from aiogram.types import CallbackQuery, Message
from sqlalchemy import delete, select

from bot.db.crud import get_or_create_user
from bot.db.models import Chat, Message as DbMessage
from bot.db.session import SessionFactory
from bot.keyboards.chats_menu import chats_list

router = Router()


@router.message(F.text == "💬 Мои чаты")
async def my_chats(message: Message) -> None:
    async with SessionFactory() as session:
        user = await get_or_create_user(session, message.from_user.id, message.from_user.username)
        chats = list((await session.scalars(select(Chat).where(Chat.user_id == user.id).order_by(Chat.updated_at.desc()).limit(20))).all())
    await message.answer("Ваши чаты:", reply_markup=chats_list(chats))


@router.callback_query(F.data.startswith("openchat:"))
async def open_chat(callback: CallbackQuery) -> None:
    chat_id = int(callback.data.split(":", 1)[1])
    async with SessionFactory() as session:
        user = await get_or_create_user(session, callback.from_user.id, callback.from_user.username)
        chat = await session.get(Chat, chat_id)
        if not chat or chat.user_id != user.id:
            await callback.answer("Чат не найден", show_alert=True)
            return
        user.current_chat_id = chat.id
        await session.commit()
    await callback.message.edit_text("Чат открыт. Продолжайте диалог.")
    await callback.answer()


@router.callback_query(F.data.startswith("delchat:"))
async def delete_chat(callback: CallbackQuery) -> None:
    chat_id = int(callback.data.split(":", 1)[1])
    async with SessionFactory() as session:
        user = await get_or_create_user(session, callback.from_user.id, callback.from_user.username)
        chat = await session.get(Chat, chat_id)
        if chat and chat.user_id == user.id:
            await session.execute(delete(DbMessage).where(DbMessage.chat_id == chat.id))
            await session.delete(chat)
            if user.current_chat_id == chat.id:
                user.current_chat_id = None
            await session.commit()
    await callback.message.edit_text("Чат удалён.")
    await callback.answer()
