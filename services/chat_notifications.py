"""
Фоновые задачи системы активности чатов.
- Авто-сообщения каждые 5-10 минут
- Уведомления о джекпоте
- Уведомления о рынке
- Проверка активности чатов
"""
import logging
import asyncio
import random
from datetime import datetime, timedelta
from typing import Optional, List
from aiogram import Bot
from db import db
from config import config
from services.activity import ActivityService, activity_tracker
from services.chat import ChatService

logger = logging.getLogger(__name__)


class ChatActivityManager:
    """
    Менеджер активности чатов.
    Управляет фоновыми задачами для всех чатов.
    """

    def __init__(self, bot: Bot):
        self.bot = bot
        self._last_auto_message: dict = {}  # chat_id -> last_message_time
        self._last_jackpot_notify: dict = {}  # chat_id -> last_notify_time
        self._last_market_notify: dict = {}  # chat_id -> last_notify_time
        self._last_message_categories: dict = {}  # chat_id -> last_category

    async def run_auto_message_task(self):
        """
        Задача авто-сообщений.
        Отправляет случайные сообщения в чаты каждые 5-10 минут.
        """
        logger.info("📢 Задача авто-сообщений запущена")

        while True:
            try:
                await asyncio.sleep(config.CHAT_ACTIVITY_CHECK_INTERVAL)

                # Получаем все чаты
                chats = db.get_top_chats(100)

                for chat in chats:
                    chat_id = chat["chat_id"]

                    # Пропускаем приватные чаты
                    if chat["chat_type"] == "private":
                        continue

                    # Проверяем, можно ли отправлять
                    last_message = self._last_auto_message.get(chat_id)
                    if not ActivityService.should_send_message(last_message):
                        continue

                    # Проверяем кулдаун чата
                    db_chat = db.get_chat(chat_id)
                    if db_chat:
                        # Проверяем, не затих ли чат
                        last_activity = activity_tracker.get_last_activity(chat_id)

                        # Если чат затих — отправляем "оживляющее" сообщение
                        if ActivityService.is_chat_silent(last_activity):
                            await self._send_silent_message(chat_id)
                            self._last_auto_message[chat_id] = datetime.now()
                            activity_tracker.record_message(chat_id)
                            continue

                    # Выбираем случайную категорию
                    category = self._get_smart_category(chat_id)

                    # Получаем сообщение
                    jackpot_amount = db.get_jackpot_bank()
                    chat_level = db_chat["level"] if db_chat else 1

                    message_text = ActivityService.get_message(
                        category=category,
                        jackpot_amount=jackpot_amount,
                        chat_level=chat_level
                    )

                    # 30% шанс упоминания пользователя
                    if ActivityService.should_mention_user():
                        active_users = activity_tracker.get_active_users(chat_id)
                        if active_users:
                            user_id = random.choice(active_users)
                            user = await self._get_user_safe(user_id)
                            if user and user.username:
                                user_message = ActivityService.get_user_message(
                                    category=category,
                                    username=f"@{user.username}"
                                )
                                if user_message:
                                    message_text = user_message

                    # Отправляем сообщение
                    await self._send_message_safe(chat_id, message_text)

                    # Записываем время отправки
                    self._last_auto_message[chat_id] = datetime.now()
                    self._last_message_categories[chat_id] = category

                    # Небольшая задержка между отправками
                    await asyncio.sleep(1)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"❌ Ошибка в задаче авто-сообщений: {e}")
                await asyncio.sleep(10)

    def _get_smart_category(self, chat_id: int) -> str:
        """
        Умный выбор категории сообщения.
        Учитывает последние события в чате.
        """
        last_category = self._last_message_categories.get(chat_id)

        # Не повторяем последнюю категорию
        categories = list(ActivityService.get_category_for_event("").keys())
        if last_category:
            categories = [c for c in categories if c != last_category]

        # Проверяем события в чате
        jackpot_amount = db.get_jackpot_bank()

        # Если джекпот большой — чаще отправляем про джекпот
        if jackpot_amount > config.JACKPOT_HIGH_THRESHOLD and random.random() < 0.5:
            return "jackpot"

        # Проверяем рынок
        if random.random() < 0.2:
            return "market"

        return random.choice(categories)

    async def _send_message_safe(self, chat_id: int, message: str):
        """Безопасная отправка сообщения."""
        try:
            await self.bot.send_message(chat_id, message)
            logger.debug(f"📢 Отправлено сообщение в чат {chat_id}")
        except Exception as e:
            logger.warning(f"Не удалось отправить сообщение в чат {chat_id}: {e}")

    async def _send_silent_message(self, chat_id: int):
        """Отправить сообщение в затихший чат."""
        message = ActivityService.get_message("chat_activity")
        await self._send_message_safe(chat_id, message)

    async def _get_user_safe(self, user_id: int):
        """Безопасное получение информации о пользователе."""
        try:
            return await self.bot.get_chat(user_id)
        except Exception:
            return None

    async def run_jackpot_notification_task(self):
        """
        Задача уведомлений о джекпоте.
        Отправляет уведомления о росте банка.
        """
        logger.info("🎰 Задача уведомлений о джекпоте запущена")

        last_bank = 0

        while True:
            try:
                await asyncio.sleep(config.CHAT_ACTIVITY_CHECK_INTERVAL * 2)

                jackpot_amount = db.get_jackpot_bank()
                time_until_draw = self._get_time_until_draw()

                # Получаем все чаты
                chats = db.get_top_chats(100)

                for chat in chats:
                    chat_id = chat["chat_id"]

                    if chat["chat_type"] == "private":
                        continue

                    # Проверяем интервал уведомлений
                    last_notify = self._last_jackpot_notify.get(chat_id)
                    if last_notify:
                        interval = timedelta(minutes=config.JACKPOT_NOTIFICATION_INTERVAL)
                        if datetime.now() - last_notify < interval:
                            continue

                    # Формируем сообщение
                    message = ActivityService.get_jackpot_message(
                        jackpot_amount=jackpot_amount,
                        time_until_draw=time_until_draw
                    )

                    # Отправляем
                    await self._send_message_safe(chat_id, message)
                    self._last_jackpot_notify[chat_id] = datetime.now()

                last_bank = jackpot_amount

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"❌ Ошибка в задаче уведомлений джекпота: {e}")
                await asyncio.sleep(10)

    def _get_time_until_draw(self) -> str:
        """Получить время до следующего розыгрыша джекпота."""
        last_draw = db.get_last_jackpot_draw()

        if not last_draw:
            return "6ч"

        next_draw = last_draw + timedelta(hours=config.JACKPOT_INTERVAL_HOURS)
        time_left = next_draw - datetime.now()

        if time_left.total_seconds() <= 0:
            return "0мин"

        hours = int(time_left.total_seconds() // 3600)
        minutes = int((time_left.total_seconds() % 3600) // 60)

        if hours > 0:
            return f"{hours}ч {minutes}мин"
        else:
            return f"{minutes}мин"

    async def run_market_notification_task(self):
        """
        Задача уведомлений о рынке.
        Отправляет уведомления об изменении цен.
        """
        logger.info("📊 Задача уведомлений о рынке запущена")

        last_prices = {}

        while True:
            try:
                await asyncio.sleep(config.CHAT_ACTIVITY_CHECK_INTERVAL * 3)

                # Получаем текущие цены
                prices = db.get_market_prices()

                # Проверяем изменения
                changed_resources = []
                for resource, data in prices.items():
                    current_price = float(data["current_price"])
                    base_price = float(data["base_price"])

                    if resource in last_prices:
                        change = ((current_price - last_prices[resource]) / last_prices[resource]) * 100
                        if abs(change) > 5:  # Изменение более 5%
                            changed_resources.append((resource, change))

                # Если есть значимые изменения — отправляем уведомления
                if changed_resources:
                    chats = db.get_top_chats(100)

                    for chat in chats:
                        chat_id = chat["chat_id"]

                        if chat["chat_type"] == "private":
                            continue

                        # Проверяем интервал
                        last_notify = self._last_market_notify.get(chat_id)
                        if last_notify:
                            interval = timedelta(minutes=config.MARKET_NOTIFICATION_INTERVAL)
                            if datetime.now() - last_notify < interval:
                                continue

                        # Формируем сообщение
                        messages = []
                        for resource, change in changed_resources[:3]:  # Максимум 3 ресурса
                            msg = ActivityService.get_market_message(resource, change)
                            messages.append(msg)

                        full_message = "\n\n".join(messages)

                        await self._send_message_safe(chat_id, full_message)
                        self._last_market_notify[chat_id] = datetime.now()

                # Сохраняем текущие цены
                last_prices = {r: float(d["current_price"]) for r, d in prices.items()}

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"❌ Ошибка в задаче уведомлений рынка: {e}")
                await asyncio.sleep(10)

    async def run_chat_level_check_task(self):
        """
        Задача проверки уровней чатов.
        Отправляет уведомления о повышении уровня.
        """
        logger.info("🏆 Задача проверки уровней чатов запущена")

        chat_levels = {}  # chat_id -> level

        while True:
            try:
                await asyncio.sleep(config.CHAT_ACTIVITY_CHECK_INTERVAL * 2)

                chats = db.get_top_chats(100)

                for chat in chats:
                    chat_id = chat["chat_id"]
                    level = chat["level"]

                    # Проверяем изменение уровня
                    if chat_id in chat_levels:
                        if level > chat_levels[chat_id]:
                            # Чат повысил уровень!
                            await self._handle_level_up(chat_id, level)

                    chat_levels[chat_id] = level

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"❌ Ошибка в задаче проверки уровней: {e}")
                await asyncio.sleep(10)

    async def _handle_level_up(self, chat_id: int, new_level: int):
        """Обработка повышения уровня чата."""
        message = ActivityService.get_level_up_message(
            new_level=new_level,
            energy_bonus=config.CHAT_LEVEL_UP_ENERGY_BONUS
        )

        await self._send_message_safe(chat_id, message)

        # Выдаём бонусы участникам
        chat_users = db.get_chat_users(chat_id)
        for user_row in chat_users:
            user_id = user_row["user_id"]
            if user_id == self.bot.id:
                continue

            from services.energy import EnergyService
            EnergyService.add_energy(user_id, config.CHAT_LEVEL_UP_ENERGY_BONUS)

        logger.info(f"🏆 Чат {chat_id} повысил уровень до {new_level}")


# Глобальный менеджер активности
activity_manager: Optional[ChatActivityManager] = None


def init_activity_manager(bot: Bot):
    """Инициализировать менеджер активности."""
    global activity_manager
    activity_manager = ChatActivityManager(bot)
    return activity_manager


async def start_activity_tasks():
    """Запустить все задачи активности."""
    if not activity_manager:
        logger.error("❌ Менеджер активности не инициализирован!")
        return

    tasks = [
        activity_manager.run_auto_message_task(),
        activity_manager.run_jackpot_notification_task(),
        activity_manager.run_market_notification_task(),
        activity_manager.run_chat_level_check_task(),
    ]

    await asyncio.gather(*tasks, return_exceptions=True)
