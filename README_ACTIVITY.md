# 📢 Система активности чатов для Telegram-бота "Микрокапитализм"

## 📋 Обзор

Система активности чатов автоматически управляет взаимодействием бота с групповыми чатами, создавая ощущение живого мира через:
- Авто-сообщения каждые 5-10 минут
- Реакцию на события игроков
- Уведомления о джекпоте и рынке
- Уровни чатов с бонусами

## 🗂️ Структура файлов

```
doll/
├── data/
│   ├── __init__.py           # Импорты data
│   └── messages.py           # 100+ сообщений для авто-отправки
├── services/
│   ├── __init__.py           # Импорты сервисов
│   ├── activity.py           # Сервис активности (логика сообщений)
│   └── chat_notifications.py # Фоновые задачи уведомлений
├── handlers/
│   ├── __init__.py           # Импорты обработчиков
│   └── chat_activity.py      # Обработчики событий чата
├── config.py                 # Конфигурация активности
├── bot.py                    # Основной файл с запуском задач
└── README_ACTIVITY.md        # Этот файл
```

## 🚀 Быстрый старт

### 1. Установка зависимостей

```bash
pip install -r requirements.txt
```

### 2. Настройка конфигурации

В `config.py` уже добавлены настройки активности:

```python
# ==================== АКТИВНОСТЬ ЧАТОВ ====================
AUTO_MESSAGE_INTERVAL_MIN: int = 5          # Мин. интервал авто-сообщений
AUTO_MESSAGE_INTERVAL_MAX: int = 10         # Макс. интервал
CHAT_MESSAGE_COOLDOWN: int = 5              # Кулдаун для чата
AUTO_MESSAGE_SEND_CHANCE: float = 0.7       # Шанс отправки (70%)
USER_MENTION_CHANCE: float = 0.3            # Шанс упоминания (30%)
CHAT_SILENT_THRESHOLD: int = 15             # Чат затих через 15 мин
CHAT_ACTIVITY_CHECK_INTERVAL: int = 60      # Проверка каждую минуту
JACKPOT_NOTIFICATION_INTERVAL: int = 30     # Уведомления джекпота
MARKET_NOTIFICATION_INTERVAL: int = 30      # Уведомления рынка
```

### 3. Запуск бота

```bash
python bot.py
```

Фоновые задачи активности запустятся автоматически!

## 📊 Компоненты системы

### 1. ActivityService (`services/activity.py`)

Основной сервис для генерации сообщений:

```python
from services.activity import ActivityService, activity_tracker

# Получить сообщение категории
message = ActivityService.get_message(
    category="money",
    jackpot_amount=500.0,
    chat_level=3
)

# Получить сообщение с упоминанием пользователя
user_message = ActivityService.get_user_message(
    category="business",
    username="@karlos",
    business="IT-компания",
    level=5
)

# Проверить, можно ли отправлять сообщение
can_send = ActivityService.should_send_message(last_message_time)

# Записать активность
activity_tracker.record_activity(chat_id, user_id)
activity_tracker.record_message(chat_id)
```

### 2. ChatActivityManager (`services/chat_notifications.py`)

Фоновые задачи для всех чатов:

```python
from services.chat_notifications import (
    init_activity_manager,
    start_activity_tasks
)

# Инициализация
init_activity_manager(bot)

# Запуск задач (async)
await start_activity_tasks()
```

**Задачи:**
- `run_auto_message_task()` — авто-сообщения
- `run_jackpot_notification_task()` — уведомления джекпота
- `run_market_notification_task()` — уведомления рынка
- `run_chat_level_check_task()` — проверка уровней чатов

### 3. Обработчики событий (`handlers/chat_activity.py`)

Обработчики для регистрации чатов и отслеживания активности:

```python
from handlers.chat_activity import router

# Автоматически регистрируется в handlers/__init__.py
# События:
# - bot_added_to_chat — добавление бота в чат
# - track_message_activity — отслеживание сообщений
# - chat_stats_command — команда /chat
# - top_chats_command — команда /topchats
```

## 📝 Категории сообщений

| Категория | Описание | Пример |
|-----------|----------|--------|
| `money` | Деньги, переводы, кредиты | "💰 Деньги любят тишину, но не в нашей игре!" |
| `market` | Рынок, цены, ресурсы | "📈 Цены на зерно растут! Успейте продать!" |
| `energy` | Энергия, регенерация | "⚡ Энергия — это новая валюта!" |
| `business` | Бизнесы, производство | "🏭 Лимонадная стоит $50. Окупается за 10 часов!" |
| `risk` | Риски, банкротство | "⚠️ Риск — дело благородное, но знайте меру!" |
| `jackpot` | Джекпот, билеты | "🎰 Джекпот уже $500! Кто сорвёт куш?" |
| `lottery` | Лотерея | "🎲 Испытай удачу! Билет стоит $10!" |
| `chat_activity` | Активность чата | "😈 В этом чате стало тихо... Кто уснул?" |
| `achievements` | Достижения, уровни | "🏆 Чат повысил уровень! Бонусы активированы!" |

## 🎯 Умная логика сообщений

### Анти-спам защита

```python
# Не чаще 1 сообщения в 5 минут в один чат
if not ActivityService.should_send_message(last_message_time):
    return

# Шанс отправки 70%
if random.random() > ActivityService.SEND_CHANCE:
    return
```

### Упоминание пользователей

```python
# 30% шанс упоминания
if ActivityService.should_mention_user():
    active_users = activity_tracker.get_active_users(chat_id)
    if active_users:
        user_id = random.choice(active_users)
        # Получить username и создать сообщение
```

### Реакция на события

```python
# Если джекпот большой — чаще отправляем про джекпот
if jackpot_amount > config.JACKPOT_HIGH_THRESHOLD:
    category = "jackpot"

# Если чат затих — отправляем "оживляющее" сообщение
if ActivityService.is_chat_silent(last_activity):
    message = ActivityService.get_message("chat_activity")
```

## 🏆 Уровни чатов

### Получение XP

| Действие | XP |
|----------|-----|
| Команда | 1 |
| Перевод | 2 |
| Лотерея | 5 |
| Новый пользователь | 10 |

### Бонусы по уровням

| Уровень | Бонус |
|---------|-------|
| 2 | +5% к доходу |
| 3 | 1 бесплатный билет джекпота |
| 4 | -10% к расходу энергии |
| 5 | +10% шанс джекпота |

### Формула уровня

```python
xp_needed = 100 * (level ** 1.5)
```

## 🔧 Настройка

### Изменение частоты сообщений

В `config.py`:

```python
# Отправлять сообщения каждые 3-7 минут
AUTO_MESSAGE_INTERVAL_MIN = 3
AUTO_MESSAGE_INTERVAL_MAX = 7

# Увеличить шанс отправки до 90%
AUTO_MESSAGE_SEND_CHANCE = 0.9

# Упоминать пользователей в 50% случаев
USER_MENTION_CHANCE = 0.5
```

### Добавление новых сообщений

В `data/messages.py`:

```python
MESSAGES = {
    "new_category": [
        "Новое сообщение 1",
        "Новое сообщение 2",
        # ...
    ],
}
```

### Отключение категории

В `services/chat_notifications.py`:

```python
# Закомментировать задачу
# await activity_manager.run_market_notification_task()
```

## 📊 Команды для пользователей

### /chat
Показать статистику текущего чата:
```
📊 Статистика чата

📛 Название: Мой чат
🏆 Уровень: 5
⭐ XP: 250 / 500
📈 Прогресс: 50.0%

🎁 Бонусы:
  • К доходу: +5%
  • К энергии: -10%
  • К джекпоту: +10%
  • Бесплатных билетов: 1
```

### /topchats
Показать топ чатов:
```
🏆 Топ чатов по уровням

🥇 Чат #1 — ур. 10 (1500 XP)
🥈 Чат #2 — ур. 8 (1200 XP)
🥉 Чат #3 — ур. 7 (900 XP)
4. Чат #4 — ур. 5 (500 XP)
```

## 🐛 Отладка

### Включить логирование

В `bot.py`:

```python
logging.basicConfig(level=logging.DEBUG)  # Вместо INFO
```

### Проверка активности чата

```python
from services.activity import activity_tracker

# Получить последнюю активность
last = activity_tracker.get_last_activity(chat_id)
print(f"Последняя активность: {last}")

# Проверить, затих ли чат
is_silent = activity_tracker.is_chat_silent(chat_id)
print(f"Чат затих: {is_silent}")
```

### Статистика отправки сообщений

Логи бота покажут:
```
📢 Отправлено сообщение в чат 123456789
🏆 Чат 123456789 повысил уровень до 5
🎰 Банк джекпота: $650.00, до розыгрыша: 2ч 15мин
```

## ⚠️ Production рекомендации

### 1. Ограничение количества чатов

```python
# Получать только топ-100 чатов
chats = db.get_top_chats(100)
```

### 2. Обработка ошибок отправки

```python
try:
    await bot.send_message(chat_id, message)
except Exception as e:
    logger.warning(f"Не удалось отправить в чат {chat_id}: {e}")
```

### 3. Мониторинг производительности

```python
# Логировать время выполнения задач
start = time.time()
# ... задача ...
logger.info(f"Задача выполнена за {time.time() - start:.2f}с")
```

## 📈 Расширение

### Добавление новой категории уведомлений

1. Добавить сообщения в `data/messages.py`
2. Создать метод в `ActivityService`
3. Добавить задачу в `ChatActivityManager`
4. Обновить конфиг в `config.py`

### Интеграция с внешними сервисами

```python
# Пример: отправка статистики в Discord webhook
async def send_to_discord(webhook_url: str, message: str):
    async with aiohttp.ClientSession() as session:
        await session.post(webhook_url, json={"content": message})
```

## 📝 Changelog

### v1.0.0 (2026-03-28)
- ✅ Базовая система авто-сообщений
- ✅ 100+ сообщений в 9 категориях
- ✅ Уровни чатов с бонусами
- ✅ Уведомления о джекпоте
- ✅ Уведомления о рынке
- ✅ Анти-спам защита
- ✅ Упоминание пользователей
- ✅ Команды /chat и /topchats

---

**Автор:** Система активности для бота "Микрокапитализм: Жизнь на 1 доллар"
