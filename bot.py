import asyncio
import requests
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from dotenv import load_dotenv

# Загружаем переменные окружения из .env
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
            [KeyboardButton(text="⬅️ Модели")]
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
        return f"❌ Ошибка связи с сервером: {str(e)}"

# ========== КОМАНДА /START ==========
@dp.message(CommandStart())
async def start(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "👋 **Добро пожаловать!**\nВыберите модель искусственного интеллекта для начала работы:", 
        reply_markup=model_kb(), 
        parse_mode="Markdown"
    )

# ========== МАППИНГ МОДЕЛЕЙ ==========
MODEL_MAP = {
    "🚀 GPT-5 Nano": "openai/gpt-5-nano",
    "🐳 DeepSeek V3": "deepseek/deepseek-chat"
}

# ========== ВЫБОР МОДЕЛИ ==========
@dp.message(F.text.in_(MODEL_MAP.keys()))
async def select_model(message: types.Message, state: FSMContext):
    model_id = MODEL_MAP[message.text]
    
    # Установка личности для каждой модели
    if "gpt-5" in model_id:
        sys_prompt = "Ты — GPT-5 Nano, новейшая модель от OpenAI. Ты эксперт во всем, помогаешь решать задачи и анализировать фото."
    else:
        sys_prompt = "Ты — DeepSeek V3, мощная языковая модель. Ты отвечаешь на вопросы пользователя точно и по делу."

    await state.set_state(ChatState.chat)
    await state.update_data(model=model_id, history=[
        {"role": "system", "content": sys_prompt}
    ])
    
    await message.answer(
        f"✅ Выбрана модель: **{message.text}**\nОтправьте текст или изображение для анализа.", 
        reply_markup=chat_kb(),
        parse_mode="Markdown"
    )

# ========== ОБРАБОТКА ЧАТА ==========
@dp.message(ChatState.chat)
async def handle_chat(message: types.Message, state: FSMContext):
    data = await state.get_data()
    model = data.get("model")
    history = data.get("history", [])

    # Кнопка сброса контекста
    if message.text == "🔄 Сброс":
        # Оставляем только системный промт
        history = [history[0]] if history else []
        await state.update_data(history=history)
        return await message.answer("♻️ Контекст текущего диалога очищен.")
    
    # Кнопка возврата к выбору моделей
    if message.text == "⬅️ Модели":
        await state.clear()
        return await message.answer("Выберите другую модель:", reply_markup=model_kb())

    user_content = []

    # 1. Если пришло ФОТО
    if message.photo:
        # Проверка: DeepSeek-Chat обычно не поддерживает Vision
        if "deepseek-chat" in model:
            return await message.answer("⚠️ DeepSeek V3 не поддерживает анализ изображений. Пожалуйста, используйте GPT-5 Nano для работы с фото.")
            
        file = await bot.get_file(message.photo[-1].file_id)
        file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file.file_path}"
        
        if message.caption:
            user_content.append({"type": "text", "text": message.caption})
        
        user_content.append({"type": "image_url", "image_url": {"url": file_url}})
    
    # 2. Если пришел ТЕКСТ
    elif message.text:
        user_content = message.text
        
    # 3. Если пришел ГОЛОС
    elif message.voice:
        return await message.answer("🎤 Голосовые сообщения пока в разработке. Пожалуйста, используйте текст.")
    
    else:
        # Игнорируем другие типы файлов (стикеры и т.д.)
        return

    # Добавляем сообщение пользователя в историю
    history.append({"role": "user", "content": user_content})

    # Визуализация ожидания
    await bot.send_chat_action(message.chat.id, "typing")
    
    # Запрос к OpenRouter
    answer = ask_openrouter(model, history)
    
    # Сохраняем ответ ассистента и обновляем историю в FSM
    history.append({"role": "assistant", "content": answer})
    await state.update_data(history=history)
    
    # Отправка ответа пользователю
    await message.answer(answer)

# ========== ЗАПУСК ==========
async def main():
    print("Бот успешно запущен и готов к работе...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("Бот остановлен.")
