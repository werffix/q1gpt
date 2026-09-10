from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot.db.models import Model


def categories(models: list[Model]) -> InlineKeyboardMarkup:
    providers = dict.fromkeys(model.provider.value for model in models)
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=p, callback_data=f"modelcat:{p}")] for p in providers])


def model_list(models: list[Model], current_id: int | None) -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(text=f"{'✅ ' if model.id == current_id else ''}{model.display_name}", callback_data=f"model:{model.id}")] for model in models]
    rows.append([InlineKeyboardButton(text="◀️ Категории", callback_data="modelcats")])
    return InlineKeyboardMarkup(inline_keyboard=rows)
