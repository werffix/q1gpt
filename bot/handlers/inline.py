import asyncio
import base64
import uuid

from aiogram import Router
from aiogram.types import ChosenInlineResult, InlineQuery, InlineQueryResultArticle, InputTextMessageContent

from bot.db.crud import get_model, get_or_create_user
from bot.db.session import SessionFactory
from bot.llm.client import LLMClient, LLMError
from bot.llm.formatting import format_answer

router = Router()
_queries: dict[str, str] = {}


@router.inline_query()
async def inline_query(query: InlineQuery) -> None:
    key = uuid.uuid4().hex[:16]
    _queries[key] = query.query.strip()
    result = InlineQueryResultArticle(id=key, title="Спросить Q1 GPT", description="Нажмите, чтобы получить ответ", input_message_content=InputTextMessageContent(message_text="⏳ Генерирую ответ…"))
    await query.answer([result], cache_time=0, is_personal=True)


@router.chosen_inline_result()
async def chosen_inline(result: ChosenInlineResult) -> None:
    prompt = _queries.pop(result.result_id, "")
    if not prompt or not result.inline_message_id:
        return
    async with SessionFactory() as session:
        user = await get_or_create_user(session, result.from_user.id, result.from_user.username)
        model = await get_model(session, user.current_model_id) if user.current_model_id else None
    if not model or model.is_image_model:
        return
    text = ""
    try:
        async for chunk in LLMClient().respond(model.api_model_id, [{"role": "user", "content": prompt}], stream=True):
            text += chunk
        formatted = format_answer(text or "Модель не вернула ответ.")
        await result.bot.edit_message_text(inline_message_id=result.inline_message_id, text=formatted.text[:4090], parse_mode=formatted.parse_mode)
    except (LLMError, Exception):
        await result.bot.edit_message_text(inline_message_id=result.inline_message_id, text="Не удалось получить ответ.", parse_mode=None)
