from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.models import AccessAttempt, AllowedUser, Chat, Message, Model, Provider, User

SEED_MODELS = [
    (Provider.OPENAI, "gpt-5.6-terra", "gpt-5.6-terra", False, True),
    (Provider.OPENAI, "gpt-5.6-luna", "gpt-5.6-luna", False, True),
    (Provider.OPENAI, "gpt-5.4-mini", "gpt-5.4-mini", False, True),
    (Provider.ANTHROPIC, "claude-sonnet-5", "claude-sonnet-5", False, True),
    (Provider.GEMINI, "gemini-3-flash-preview", "gemini-3-flash-preview", False, True),
    (Provider.GEMINI, "gemini-3.7-flash", "gemini-3.7-flash", False, True),
    (Provider.GEMINI, "gemini-3.8-flash", "gemini-3.8-flash", False, True),
    (Provider.XAI, "grok-4-6", "grok-4-6", False, False),
    (Provider.DEEPSEEK, "deepseek-v4-flash", "deepseek-v4-flash", False, False),
    (Provider.DEEPSEEK, "deepseek-v4-flash-vision-exp", "deepseek-v4-flash-vision-exp", False, True),
    (Provider.IMAGES, "gpt-image-2.5", "gpt-image-2.5", True, True),
    (Provider.IMAGES, "nano-banana-pro", "nano-banana-pro", True, True),
]


async def seed_models(session: AsyncSession) -> None:
    if await session.scalar(select(func.count(Model.id))):
        return
    session.add_all(
        [Model(provider=p, display_name=n, api_model_id=api, is_image_model=img, supports_vision=vision, sort_order=i) for i, (p, n, api, img, vision) in enumerate(SEED_MODELS)]
    )
    await session.commit()


async def get_or_create_user(session: AsyncSession, telegram_id: int, username: str | None) -> User:
    user = await session.scalar(select(User).where(User.telegram_id == telegram_id))
    if not user:
        user = User(telegram_id=telegram_id, username=username)
        session.add(user)
    else:
        user.username = username
    await session.flush()
    if user.current_model_id is None:
        model = await session.scalar(select(Model).where(Model.is_active == True).order_by(Model.sort_order))
        if model:
            user.current_model_id = model.id
    await session.commit()
    return user


async def is_allowed(session: AsyncSession, telegram_id: int, username: str | None) -> bool:
    normalized = username.removeprefix("@").lower() if username else None
    conditions = [AllowedUser.telegram_id == telegram_id]
    if normalized:
        conditions.append(AllowedUser.username == normalized)
    query = select(AllowedUser).where(or_(*conditions))
    return await session.scalar(query) is not None


async def log_access_attempt(session: AsyncSession, telegram_id: int, username: str | None) -> None:
    session.add(AccessAttempt(telegram_id=telegram_id, username=username))
    await session.commit()


async def list_active_models(session: AsyncSession) -> list[Model]:
    return list((await session.scalars(select(Model).where(Model.is_active == True).order_by(Model.sort_order))).all())


async def get_model(session: AsyncSession, model_id: int) -> Model | None:
    return await session.get(Model, model_id)


async def get_or_create_chat(session: AsyncSession, user: User, model: Model) -> Chat:
    if user.current_chat_id:
        chat = await session.get(Chat, user.current_chat_id)
        if chat and chat.model_id == model.id:
            return chat
    chat = Chat(user_id=user.id, model_id=model.id)
    session.add(chat)
    await session.flush()
    user.current_chat_id = chat.id
    await session.commit()
    return chat


async def add_message(session: AsyncSession, chat_id: int, role: str, content: str, has_image: bool = False) -> Message:
    message = Message(chat_id=chat_id, role=role, content=content, has_image=has_image)
    session.add(message)
    await session.commit()
    return message


async def get_context(session: AsyncSession, chat_id: int, limit: int = 20) -> list[Message]:
    rows = list((await session.scalars(select(Message).where(Message.chat_id == chat_id).order_by(Message.created_at.desc()).limit(limit))).all())
    return list(reversed(rows))
