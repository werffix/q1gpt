from aiogram import F, Router
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select

from bot.db.crud import get_model, get_or_create_user, list_active_models
from bot.db.models import Model, Provider
from bot.db.session import SessionFactory
from bot.keyboards.models_menu import categories, model_list

router = Router()


@router.message(F.text == "🤖 Выбор модели")
async def choose_model(message: Message) -> None:
    async with SessionFactory() as session:
        models = await list_active_models(session)
        user = await get_or_create_user(session, message.from_user.id, message.from_user.username)
        await message.answer("Выберите категорию:", reply_markup=categories(models))


@router.callback_query(F.data == "modelcats")
async def show_categories(callback: CallbackQuery) -> None:
    async with SessionFactory() as session:
        models = await list_active_models(session)
    await callback.message.edit_text("Выберите категорию:", reply_markup=categories(models))
    await callback.answer()


@router.callback_query(F.data.startswith("modelcat:"))
async def show_models(callback: CallbackQuery) -> None:
    provider = callback.data.split(":", 1)[1]
    async with SessionFactory() as session:
        models = list((await session.scalars(select(Model).where(Model.provider == Provider(provider), Model.is_active == True).order_by(Model.sort_order))).all())
        user = await get_or_create_user(session, callback.from_user.id, callback.from_user.username)
    await callback.message.edit_text(f"Модели: {provider}", reply_markup=model_list(models, user.current_model_id))
    await callback.answer()


@router.callback_query(F.data.startswith("model:"))
async def set_model(callback: CallbackQuery) -> None:
    model_id = int(callback.data.split(":", 1)[1])
    async with SessionFactory() as session:
        user = await get_or_create_user(session, callback.from_user.id, callback.from_user.username)
        model = await get_model(session, model_id)
        if not model or not model.is_active:
            await callback.answer("Модель недоступна", show_alert=True)
            return
        user.current_model_id = model.id
        user.current_chat_id = None
        await session.commit()
    await callback.message.edit_text(f"✅ Текущая модель: {model.display_name}")
    await callback.answer()
