from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot.db.models import Chat


def chats_list(chats: list[Chat]) -> InlineKeyboardMarkup:
    rows = []
    for chat in chats:
        title = (chat.title or "Новый чат")[:35]
        rows.append([InlineKeyboardButton(text=title, callback_data=f"openchat:{chat.id}"), InlineKeyboardButton(text="🗑", callback_data=f"delchat:{chat.id}")])
    return InlineKeyboardMarkup(inline_keyboard=rows or [[InlineKeyboardButton(text="Чатов пока нет", callback_data="noop")]])
