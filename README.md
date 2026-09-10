# Q1 GPT Telegram bot

Telegram-бот на aiogram 3.x для общения с моделями через Responses API шлюза `vibecode.moe`. Веб-админка в проект не включена: управление доступом и моделями выполняется командами администратора в самом боте.

## Запуск

1. Создайте бота через [@BotFather](https://t.me/BotFather), получите токен и включите inline mode командой `/setinline`.
2. Скопируйте `.env.example` в `.env` и заполните `BOT_TOKEN`, `LLM_API_KEY`, `ADMIN_IDS`.
3. Установите зависимости: `python -m pip install -r requirements.txt`.
4. Запустите: `python -m bot.main`.

При первом запуске создаётся SQLite-база `bot.db` и заполняется каталог моделей. Для PostgreSQL достаточно указать соответствующий async URL SQLAlchemy в `DATABASE_URL`.

## Команды администратора

- `/grant <id или @username> [комментарий]`
- `/revoke <id или @username>`
- `/users`, `/models`, `/model_set <id> <api_model_id>`, `/model_toggle <id>`, `/stats`

Администраторы из `ADMIN_IDS` проходят проверку доступа автоматически. Остальных пользователей нужно добавить через `/grant`.

## Возможности

Есть выбор модели по категориям, сохранение чатов и контекста, потоковые ответы, обработка фото для vision-моделей, генерация изображений, inline mode и безопасное HTML-форматирование Markdown-ответов.
