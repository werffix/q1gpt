from aiogram.types import KeyboardButton, ReplyKeyboardMarkup


def main_menu(is_admin: bool = False) -> ReplyKeyboardMarkup:
    keyboard = [
        [KeyboardButton(text="➕ Новый чат")],
        [KeyboardButton(text="🤖 Выбор модели"), KeyboardButton(text="💬 Мои чаты")],
    ]
    if is_admin:
        keyboard.append([KeyboardButton(text="⚙️ Админ-панель")])
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)
