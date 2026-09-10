from aiogram.types import KeyboardButton, ReplyKeyboardMarkup


def main_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="➕ Новый чат")],
        [KeyboardButton(text="🤖 Выбор модели"), KeyboardButton(text="💬 Мои чаты")],
    ], resize_keyboard=True)
