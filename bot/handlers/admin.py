from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy import delete, func, select

from bot.config import get_settings
from bot.db.models import AllowedUser, Message as DbMessage, Model, User
from bot.db.session import SessionFactory

router = Router()


def _admin(message: Message) -> bool:
    return message.from_user.id in get_settings().admin_id_set


@router.message(Command("grant"))
async def grant(message: Message) -> None:
    if not _admin(message): return
    parts = message.text.split(maxsplit=2)
    if len(parts) < 2:
        await message.answer("Использование: /grant <id или @username> [комментарий]"); return
    target, note = parts[1], parts[2] if len(parts) > 2 else None
    async with SessionFactory() as session:
        row = AllowedUser(added_by=message.from_user.id, note=note)
        if target.lstrip("-").isdigit(): row.telegram_id = int(target)
        else: row.username = target.removeprefix("@").lower()
        session.add(row)
        try: await session.commit()
        except Exception:
            await session.rollback()
            await message.answer("Такой пользователь уже есть."); return
    await message.answer("✅ Доступ выдан.")


@router.message(Command("revoke"))
async def revoke(message: Message) -> None:
    if not _admin(message): return
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2: await message.answer("Использование: /revoke <id или @username>"); return
    target = parts[1].removeprefix("@").lower()
    async with SessionFactory() as session:
        query = delete(AllowedUser).where(AllowedUser.telegram_id == int(target) if target.lstrip("-").isdigit() else AllowedUser.username == target)
        result = await session.execute(query); await session.commit()
    await message.answer("✅ Доступ отозван." if result.rowcount else "Пользователь не найден.")


@router.message(Command("users"))
async def users(message: Message) -> None:
    if not _admin(message): return
    async with SessionFactory() as session:
        rows = list((await session.scalars(select(AllowedUser).order_by(AllowedUser.added_at.desc()).limit(50))).all())
    text = "\n".join(f"{row.telegram_id or '@'+(row.username or '')}" for row in rows) or "Список пуст."
    await message.answer(text)


@router.message(Command("models"))
async def models(message: Message) -> None:
    if not _admin(message): return
    async with SessionFactory() as session:
        rows = list((await session.scalars(select(Model).order_by(Model.sort_order))).all())
    await message.answer("\n".join(f"{'✅' if m.is_active else '⛔'} {m.id}: {m.display_name} → {m.api_model_id}" for m in rows))


@router.message(Command("model_set"))
async def model_set(message: Message) -> None:
    if not _admin(message): return
    parts = message.text.split(maxsplit=2)
    if len(parts) != 3:
        await message.answer("Использование: /model_set <id> <api_model_id>"); return
    async with SessionFactory() as session:
        model = await session.get(Model, int(parts[1]))
        if not model:
            await message.answer("Модель не найдена."); return
        model.api_model_id = parts[2]
        await session.commit()
    await message.answer("✅ API model id обновлён.")


@router.message(Command("model_toggle"))
async def model_toggle(message: Message) -> None:
    if not _admin(message): return
    parts = message.text.split(maxsplit=1)
    if len(parts) != 2 or not parts[1].isdigit():
        await message.answer("Использование: /model_toggle <id>"); return
    async with SessionFactory() as session:
        model = await session.get(Model, int(parts[1]))
        if not model:
            await message.answer("Модель не найдена."); return
        model.is_active = not model.is_active
        await session.commit()
        status = "включена" if model.is_active else "выключена"
    await message.answer(f"✅ Модель {status}.")


@router.message(Command("stats"))
async def stats(message: Message) -> None:
    if not _admin(message): return
    async with SessionFactory() as session:
        users_count = await session.scalar(select(func.count(User.id)))
        messages_count = await session.scalar(select(func.count(DbMessage.id)))
    await message.answer(f"Пользователей: {users_count}\nСообщений: {messages_count}")
