# Q1 GPT Telegram bot

Telegram-бот на aiogram 3.x для общения с моделями через Responses API шлюза `vibecode.moe`. Веб-админка в проект не включена: управление доступом и моделями доступно из Telegram-кнопки «⚙️ Админ-панель», которая отображается только администраторам.

## Запуск

1. Создайте бота через [@BotFather](https://t.me/BotFather), получите токен и включите inline mode командой `/setinline`.
2. Скопируйте `.env.example` в `.env` и заполните значения.
3. Установите зависимости: `python3 -m pip install -r requirements.txt`.
4. Запустите: `python3 -m bot.main`.

При первом запуске создаётся SQLite-база `bot.db` и заполняется каталог моделей. Для PostgreSQL достаточно указать соответствующий async URL SQLAlchemy в `DATABASE_URL`.

## Пример `.env`

```dotenv
BOT_TOKEN=123456789:AAExampleBotToken
LLM_API_KEY=your-vibecode-api-key
LLM_BASE_URL=https://vibecode.moe/v1/responses
DATABASE_URL=sqlite+aiosqlite:///./bot.db
ADMIN_IDS=123456789,987654321
MAX_CONTEXT_MESSAGES=20
LLM_TIMEOUT=120
```

`LLM_BASE_URL` можно указать как полный endpoint `https://vibecode.moe/v1/responses` или как базовый URL, к которому клиент добавит `/responses`. `ADMIN_IDS` содержит числовые Telegram ID через запятую. Администраторы проходят проверку доступа автоматически. Через админ-панель можно выдавать и отзывать доступ, добавлять и включать модели, менять их API ID и просматривать статистику.

## Автозапуск

### Linux: systemd

Создайте `/etc/systemd/system/q1-gpt.service`, заменив пути и пользователя:

```ini
[Unit]
Description=Q1 GPT Telegram bot
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=your-user
WorkingDirectory=/opt/q1-gpt
ExecStart=/usr/bin/python3 -m bot.main
Restart=always
RestartSec=5
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
```

Затем выполните:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now q1-gpt
sudo systemctl status q1-gpt
```

Логи: `journalctl -u q1-gpt -f`.

### macOS: launchd

Создайте `~/Library/LaunchAgents/com.q1gpt.bot.plist`, заменив пути на свои:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>com.q1gpt.bot</string>
  <key>WorkingDirectory</key><string>/Users/your-user/q1-gpt</string>
  <key>ProgramArguments</key><array>
    <string>/usr/bin/python3</string><string>-m</string><string>bot.main</string>
  </array>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
  <key>StandardOutPath</key><string>/Users/your-user/q1-gpt/launchd.log</string>
  <key>StandardErrorPath</key><string>/Users/your-user/q1-gpt/launchd-error.log</string>
</dict></plist>
```

Загрузите задачу: `launchctl load -w ~/Library/LaunchAgents/com.q1gpt.bot.plist`. Для остановки: `launchctl unload -w ~/Library/LaunchAgents/com.q1gpt.bot.plist`.

## Возможности

Есть выбор модели по категориям, сохранение чатов и контекста, потоковые ответы, обработка фото для vision-моделей, генерация изображений, inline mode и безопасное HTML-форматирование Markdown-ответов.
