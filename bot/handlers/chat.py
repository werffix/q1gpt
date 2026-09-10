import asyncio
import base64
import io
import logging

from aiogram import F, Router
from aiogram.types import BufferedInputFile, Message

from bot.config import get_settings
from bot.db.crud import add_message, get_context, get_model, get_or_create_chat, get_or_create_user
from bot.db.session import SessionFactory
from bot.llm.client import LLMClient, LLMError
from bot.llm.formatting import format_answer

router = Router()
logger = logging.getLogger(__name__)


async def _file_data(message: Message) -> str | None:
    if not message.photo:
        return None
    file = await message.bot.get_file(message.photo[-1].file_id)
    buffer = io.BytesIO()
    await message.bot.download_file(file.file_path, buffer)
    return "data:image/jpeg;base64," + base64.b64encode(buffer.getvalue()).decode()


async def _run_chat(message: Message, prompt: str, image_url: str | None = None) -> None:
    async with SessionFactory() as session:
        user = await get_or_create_user(session, message.from_user.id, message.from_user.username)
        model = await get_model(session, user.current_model_id) if user.current_model_id else None
        if not model:
            await message.answer("Сначала выберите модель через меню.")
            return
        chat = await get_or_create_chat(session, user, model)
        await add_message(session, chat.id, "user", prompt, bool(image_url))
        context = await get_context(session, chat.id, get_settings().max_context_messages)
        if not chat.title:
            chat.title = prompt[:200]
            await session.commit()
    if image_url and not model.supports_vision and not model.is_image_model:
        await message.answer("Эта модель не поддерживает изображения. Выберите vision-модель.")
        return
    await message.bot.send_chat_action(message.chat.id, "typing")
    if model.is_image_model:
        try:
            result = await LLMClient().generate_image(model.api_model_id, prompt, [image_url] if image_url else None)
            if isinstance(result, bytes):
                await message.answer_photo(BufferedInputFile(result, filename="generated.png"))
            else:
                await message.answer_photo(result)
            return
        except LLMError as exc:
            await message.answer(str(exc))
            return
    messages = [{"role": item.role, "content": item.content} for item in context]
    sent = await message.answer("⏳ Генерирую ответ…")
    full = ""
    last_edit = 0.0
    try:
        async for chunk in LLMClient().respond(model.api_model_id, messages, [image_url] if image_url else None):
            full += chunk
            now = asyncio.get_running_loop().time()
            if now - last_edit >= 1.0 and full:
                try:
                    await sent.edit_text(full[:4090], parse_mode=None)
                    last_edit = now
                except Exception:
                    logger.debug("Telegram edit failed", exc_info=True)
        if not full:
            full = "Модель не вернула текстовый ответ."
        formatted = format_answer(full)
        try:
            await sent.edit_text(formatted.text[:4090], parse_mode=formatted.parse_mode)
            if len(formatted.text) > 4090:
                for offset in range(4090, len(formatted.text), 4090):
                    await message.answer(formatted.text[offset:offset + 4090], parse_mode=formatted.parse_mode)
        except Exception:
            await sent.edit_text(full[:4090], parse_mode=None)
        async with SessionFactory() as session:
            await add_message(session, chat.id, "assistant", full)
    except LLMError as exc:
        await sent.edit_text(str(exc))


@router.message(F.photo)
async def photo_message(message: Message) -> None:
    await _run_chat(message, message.caption or "Опиши это изображение.", await _file_data(message))


@router.message(F.text == "➕ Новый чат")
async def new_chat(message: Message) -> None:
    async with SessionFactory() as session:
        user = await get_or_create_user(session, message.from_user.id, message.from_user.username)
        user.current_chat_id = None
        await session.commit()
    await message.answer("✅ Новый чат создан.")


@router.message(F.text)
async def text_message(message: Message) -> None:
    if message.text.startswith("/") or message.text in {"🤖 Выбор модели", "💬 Мои чаты"}:
        return
    await _run_chat(message, message.text)
