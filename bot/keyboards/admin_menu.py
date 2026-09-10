from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot.db.models import AllowedUser, Model


def panel() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👥 Доступ", callback_data="admin:access")],
        [InlineKeyboardButton(text="🤖 Модели", callback_data="admin:models")],
        [InlineKeyboardButton(text="📊 Статистика", callback_data="admin:stats")],
    ])


def back() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="◀️ Админ-панель", callback_data="admin:home")]])


def access_menu(users: list[AllowedUser]) -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(text="➕ Выдать доступ", callback_data="admin:grant")]]
    for user in users:
        label = str(user.telegram_id) if user.telegram_id else f"@{user.username}"
        rows.append([InlineKeyboardButton(text=f"❌ {label}", callback_data=f"admin:revoke:{user.id}")])
    rows.append([InlineKeyboardButton(text="◀️ Назад", callback_data="admin:home")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def models_menu(models: list[Model]) -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(text="➕ Добавить модель", callback_data="admin:addmodel")]]
    for model in models:
        state = "✅" if model.is_active else "⛔"
        rows.append([
            InlineKeyboardButton(text=f"{state} {model.display_name}", callback_data=f"admin:model:{model.id}"),
            InlineKeyboardButton(text="Вкл/выкл", callback_data=f"admin:toggle:{model.id}"),
        ])
    rows.append([InlineKeyboardButton(text="◀️ Назад", callback_data="admin:home")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def model_menu(model: Model) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Изменить API ID", callback_data=f"admin:editapi:{model.id}")],
        [InlineKeyboardButton(text="Вкл/выкл", callback_data=f"admin:toggle:{model.id}")],
        [InlineKeyboardButton(text="◀️ К моделям", callback_data="admin:models")],
    ])
