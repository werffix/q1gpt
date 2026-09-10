import html

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from sqlalchemy import delete, func, select

from bot.config import get_settings
from bot.db.models import AllowedUser, Message as DbMessage, Model, Provider, User
from bot.db.session import SessionFactory
from bot.keyboards.admin_menu import access_menu, back, model_menu, models_menu, panel
from bot.keyboards.main_menu import main_menu

router = Router()


class AdminStates(StatesGroup):
    waiting_grant = State()
    waiting_api_id = State()
    waiting_new_model = State()


def _is_admin(user_id: int) -> bool:
    return user_id in get_settings().admin_id_set


async def _deny(callback: CallbackQuery) -> bool:
    if _is_admin(callback.from_user.id):
        return False
    await callback.answer("Нет доступа", show_alert=True)
    return True


async def _render_models(callback: CallbackQuery) -> None:
    async with SessionFactory() as session:
        models = list((await session.scalars(select(Model).order_by(Model.sort_order))).all())
    await callback.message.edit_text("🤖 Управление моделями", reply_markup=models_menu(models))


@router.message(F.text == "⚙️ Админ-панель")
async def open_panel(message: Message) -> None:
    if _is_admin(message.from_user.id):
        await message.answer("⚙️ Админ-панель", reply_markup=panel())


@router.callback_query(F.data == "admin:home")
async def admin_home(callback: CallbackQuery, state: FSMContext) -> None:
    if await _deny(callback): return
    await state.clear()
    await callback.message.edit_text("⚙️ Админ-панель", reply_markup=panel())
    await callback.answer()


@router.callback_query(F.data == "admin:access")
async def access(callback: CallbackQuery) -> None:
    if await _deny(callback): return
    async with SessionFactory() as session:
        users = list((await session.scalars(select(AllowedUser).order_by(AllowedUser.added_at.desc()).limit(50))).all())
    await callback.message.edit_text("👥 Пользователи с доступом\nНажмите на пользователя, чтобы отозвать доступ.", reply_markup=access_menu(users))
    await callback.answer()


@router.callback_query(F.data == "admin:grant")
async def start_grant(callback: CallbackQuery, state: FSMContext) -> None:
    if await _deny(callback): return
    await state.set_state(AdminStates.waiting_grant)
    await callback.message.edit_text("Введите Telegram ID или @username. Можно добавить комментарий после пробела.\n\nНапример: <code>123456789 тестовый доступ</code>", reply_markup=back())
    await callback.answer()


@router.message(AdminStates.waiting_grant)
async def finish_grant(message: Message, state: FSMContext) -> None:
    if not _is_admin(message.from_user.id): return
    parts = message.text.split(maxsplit=1)
    target = parts[0].strip()
    note = parts[1].strip() if len(parts) > 1 else None
    if not target.lstrip("-").isdigit() and not target.startswith("@"):
        await message.answer("Введите числовой ID или username с символом @.")
        return
    async with SessionFactory() as session:
        row = AllowedUser(added_by=message.from_user.id, note=note)
        if target.lstrip("-").isdigit(): row.telegram_id = int(target)
        else: row.username = target.removeprefix("@").lower()
        session.add(row)
        try:
            await session.commit()
        except Exception:
            await session.rollback()
            await message.answer("Такой пользователь уже есть.")
            return
    await state.clear()
    await message.answer("✅ Доступ выдан.", reply_markup=main_menu(True))


@router.callback_query(F.data.startswith("admin:revoke:"))
async def revoke(callback: CallbackQuery) -> None:
    if await _deny(callback): return
    row_id = int(callback.data.rsplit(":", 1)[1])
    async with SessionFactory() as session:
        await session.execute(delete(AllowedUser).where(AllowedUser.id == row_id))
        await session.commit()
        users = list((await session.scalars(select(AllowedUser).order_by(AllowedUser.added_at.desc()).limit(50))).all())
    await callback.message.edit_text("👥 Пользователи с доступом", reply_markup=access_menu(users))
    await callback.answer("Доступ отозван")


@router.callback_query(F.data == "admin:models")
async def show_models(callback: CallbackQuery) -> None:
    if await _deny(callback): return
    await _render_models(callback)
    await callback.answer()


@router.callback_query(F.data.startswith("admin:model:"))
async def show_model(callback: CallbackQuery) -> None:
    if await _deny(callback): return
    model_id = int(callback.data.rsplit(":", 1)[1])
    async with SessionFactory() as session:
        model = await session.get(Model, model_id)
    if not model:
        await callback.answer("Модель не найдена", show_alert=True); return
    await callback.message.edit_text(f"🤖 <b>{html.escape(model.display_name)}</b>\nПровайдер: {model.provider.value}\nAPI ID: <code>{html.escape(model.api_model_id)}</code>\nСтатус: {'включена' if model.is_active else 'выключена'}", reply_markup=model_menu(model))
    await callback.answer()


@router.callback_query(F.data.startswith("admin:toggle:"))
async def toggle_model(callback: CallbackQuery) -> None:
    if await _deny(callback): return
    model_id = int(callback.data.rsplit(":", 1)[1])
    async with SessionFactory() as session:
        model = await session.get(Model, model_id)
        if not model:
            await callback.answer("Модель не найдена", show_alert=True); return
        model.is_active = not model.is_active
        await session.commit()
        enabled = model.is_active
    await callback.answer("Включена" if enabled else "Выключена")
    await _render_models(callback)


@router.callback_query(F.data.startswith("admin:editapi:"))
async def start_api_edit(callback: CallbackQuery, state: FSMContext) -> None:
    if await _deny(callback): return
    model_id = int(callback.data.rsplit(":", 1)[1])
    await state.update_data(model_id=model_id)
    await state.set_state(AdminStates.waiting_api_id)
    await callback.message.edit_text("Введите новый API model ID:", reply_markup=back())
    await callback.answer()


@router.callback_query(F.data == "admin:addmodel")
async def start_new_model(callback: CallbackQuery, state: FSMContext) -> None:
    if await _deny(callback): return
    await state.set_state(AdminStates.waiting_new_model)
    await callback.message.edit_text(
        "Введите модель через точку с запятой:\n"
        "<code>Провайдер; Публичное имя; API ID; vision; image</code>\n\n"
        "Провайдер: OpenAI, Anthropic, Gemini, XAI, Deepseek или Images.\n"
        "Для vision и image используйте да или нет.",
        reply_markup=back(),
    )
    await callback.answer()


@router.message(AdminStates.waiting_new_model)
async def finish_new_model(message: Message, state: FSMContext) -> None:
    if not _is_admin(message.from_user.id): return
    fields = [field.strip() for field in message.text.split(";")]
    if len(fields) != 5:
        await message.answer("Нужно ровно пять значений, разделённых точкой с запятой.")
        return
    provider_name, display_name, api_model_id, vision, image = fields
    try:
        provider = Provider(provider_name)
    except ValueError:
        await message.answer("Неизвестный провайдер. Используйте значение из примера.")
        return
    truthy = {"да", "yes", "true", "1"}
    async with SessionFactory() as session:
        next_order = (await session.scalar(select(func.max(Model.sort_order)))) or 0
        session.add(Model(
            provider=provider,
            display_name=display_name,
            api_model_id=api_model_id,
            supports_vision=vision.lower() in truthy,
            is_image_model=image.lower() in truthy,
            sort_order=next_order + 1,
        ))
        await session.commit()
    await state.clear()
    await message.answer("✅ Модель добавлена.", reply_markup=main_menu(True))


@router.message(AdminStates.waiting_api_id)
async def finish_api_edit(message: Message, state: FSMContext) -> None:
    if not _is_admin(message.from_user.id): return
    data = await state.get_data()
    async with SessionFactory() as session:
        model = await session.get(Model, data.get("model_id"))
        if not model:
            await state.clear(); await message.answer("Модель не найдена."); return
        model.api_model_id = message.text.strip()
        await session.commit()
    await state.clear()
    await message.answer("✅ API model ID обновлён.", reply_markup=main_menu(True))


@router.callback_query(F.data == "admin:stats")
async def stats(callback: CallbackQuery) -> None:
    if await _deny(callback): return
    async with SessionFactory() as session:
        users_count = await session.scalar(select(func.count(User.id)))
        messages_count = await session.scalar(select(func.count(DbMessage.id)))
        allowed_count = await session.scalar(select(func.count(AllowedUser.id)))
    await callback.message.edit_text(f"📊 Статистика\n\nПользователей: <b>{users_count}</b>\nВ whitelist: <b>{allowed_count}</b>\nСообщений: <b>{messages_count}</b>", reply_markup=back())
    await callback.answer()
