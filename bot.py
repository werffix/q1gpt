import asyncio
import requests
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, FSInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
API_KEY = os.getenv("OPENROUTER_API_KEY")

bot = Bot(BOT_TOKEN)
dp = Dispatcher()

# ========== СОСТОЯНИЯ ==========
class ChatState(StatesGroup):
    chat = State()

# ========== КЛАВИАТУРЫ ==========
def model_kb():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🚀 GPT-5 Nano")],
            [KeyboardButton(text="🐳 DeepSeek V3")]
        ],
        resize_keyboard=True
    )

def chat_kb():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🔄 Сброс")],
            [KeyboardButton(text="⬅️ Назад в меню")]
        ],
        resize_keyboard=True
    )

# ========== ЛОГИКА API ==========
def ask_openrouter(model, messages):
    try:
        r = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": model,
                "messages": messages
            },
            timeout=90
        )
        data = r.json()
        if "error" in data:
            return f"⚠️ Ошибка API: {data['error'].get('message')}"
        return data["choices"][0]["message"]["content"]
    except Exception as e:
        return f"❌ Ошибка связи: {str(e)}"

# ========== ГЛАВНОЕ МЕНЮ ==========
async def send_main_menu(message: types.Message):
    menu_text = "👾 Добро пожаловать в q1 gpt\n\n👀 Выберите модель ИИ для начала работы"
    photo_path = "gpt-menu.jpg"
    
    if os.path.exists(photo_path):
        photo = FSInputFile(photo_path)
        await message.answer_photo(
            photo=photo,
            caption=menu_text,
            reply_markup=model_kb()
        )
    else:
        # Если картинки нет, просто шлем текст, чтобы бот не упал
        await message.answer(menu_text, reply_markup=model_kb())

# ========== КОМАНДА /START ==========
@dp.message(CommandStart())
async def start(message: types.Message, state: FSMContext):
    await state.clear()
    await send_main_menu(message)

# ========== МАППИНГ МОДЕЛЕЙ ==========
MODEL_MAP = {
    "🚀 GPT-5 Nano": "openai/gpt-5-nano",
    "🐳 DeepSeek V3": "deepseek/deepseek-chat"
}

# ========== ВЫБОР МОДЕЛИ ==========
@dp.message(F.text.in_(MODEL_MAP.keys()))
async def select_model(message: types.Message, state: FSMContext):
    model_id = MODEL_MAP[message.text]
    
    if "gpt-5" in model_id:
        sys_prompt = "Ты — GPT-5 Nano от OpenAI."
        welcome_text = "✅ Выбрана модель: 🚀 GPT-5 Nano\n\nОтправьте текст или изображение."
    else:
        sys_prompt = "Ты — DeepSeek V3."
        welcome_text = "✅ Выбрана модель: 🐳 DeepSeek V3\n\nНапиши свой вопрос"

    await state.set_state(ChatState.chat)
    await state.update_data(model=model_id, history=[
        {"role": "system", "content": sys_prompt}
    ])
    
    await message.answer(welcome_text, reply_markup=chat_kb())

# ========== ОБРАБОТКА ЧАТА ==========
@dp.message(ChatState.chat)
async def handle_chat(message: types.Message, state: FSMContext):
    data = await state.get_data()
    model = data.get("model")
    history = data.get("history", [])

    # Кнопка назад
    if message.text == "⬅️ Назад в меню":
        await state.clear()
        return await send_main_menu(message)

    # Кнопка сброса
    if message.text == "🔄 Сброс":
        history = [history[0]] if history else []
        await state.update_data(history=history)
        return await message.answer("♻️ Контекст очищен.")

    user_content = []

    # Обработка фото
    if message.photo:
        if "deepseek-chat" in model:
            return await message.answer("⚠️ DeepSeek V3 не поддерживает фото. Используйте GPT-5 Nano.")
            
        file = await bot.get_file(message.photo[-1].file_id)
        file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file.file_path}"
        
        if message.caption:
            user_content.append({"type": "text", "text": message.caption})
        user_content.append({"type": "image_url", "image_url": {"url": file_url}})
    
    # Обработка текста
    elif message.text:
        user_content = message.text
    else:
        return

    history.append({"role": "user", "content": user_content})
    await bot.send_chat_action(message.chat.id, "typing")
    
    answer = ask_openrouter(model, history)
    
    history.append({"role": "assistant", "content": answer})
    await state.update_data(history=history)
    await message.answer(answer)

# ========== ЗАПУСК ==========
async def main():
    print("Бот запущен...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
