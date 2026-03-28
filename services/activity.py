"""
Сервис активности чатов.
Автоматические сообщения, реакция на события, анти-спам.
"""
import random
import asyncio
from datetime import datetime, timedelta
from typing import Optional, List, Dict
from data.messages import MESSAGES, USER_MESSAGES


class ActivityService:
    """
    Система активности чатов:
    - Авто-сообщения каждые 5-10 минут
    - Реакция на события игроков
    - Упоминание пользователей
    - Анти-спам защита
    """

    # Кулдаун между сообщениями в один чат (минуты)
    COOLDOWN_MINUTES = 5
    # Шанс отправки сообщения (70%)
    SEND_CHANCE = 0.7
    # Шанс упоминания пользователя (30%)
    MENTION_CHANCE = 0.3
    # Время неактивности чата до сообщения "затих" (минуты)
    SILENT_THRESHOLD_MINUTES = 15

    @classmethod
    def get_message(cls, category: str, jackpot_amount: float = 0, chat_level: int = 1) -> str:
        """
        Получить случайное сообщение из категории.

        Args:
            category: Категория сообщения (money, market, energy, business, risk, jackpot, lottery, chat_activity, achievements)
            jackpot_amount: Текущий размер джекпота для подстановки
            chat_level: Уровень чата для подстановки

        Returns:
            Текст сообщения
        """
        messages = MESSAGES.get(category, MESSAGES["money"])
        message = random.choice(messages)

        # Подстановка динамических значений
        message = message.replace("{amount}", f"{jackpot_amount:.0f}")
        message = message.replace("{time}", f"{random.randint(1, 5)}ч")
        message = message.replace("{last_amount}", f"{random.randint(100, 500):.0f}")
        message = message.replace("{level}", str(chat_level))

        return message

    @classmethod
    def get_user_message(cls, category: str, username: str, **kwargs) -> Optional[str]:
        """
        Получить сообщение с упоминанием пользователя.

        Args:
            category: Категория сообщения
            username: Имя пользователя для упоминания
            **kwargs: Дополнительные параметры для подстановки

        Returns:
            Текст сообщения или None
        """
        messages = USER_MESSAGES.get(category, [])
        if not messages:
            return None

        message = random.choice(messages)
        message = message.replace("{user}", username)

        # Подстановка дополнительных параметров
        for key, value in kwargs.items():
            message = message.replace(f"{{{key}}}", str(value))

        return message

    @classmethod
    def should_send_message(cls, last_message_time: Optional[datetime]) -> bool:
        """
        Проверить, можно ли отправлять сообщение (анти-спам).

        Args:
            last_message_time: Время последнего сообщения в чате

        Returns:
            True если можно отправлять
        """
        # Шанс отправки
        if random.random() > cls.SEND_CHANCE:
            return False

        # Проверка кулдауна
        if last_message_time:
            cooldown_end = last_message_time + timedelta(minutes=cls.COOLDOWN_MINUTES)
            if datetime.now() < cooldown_end:
                return False

        return True

    @classmethod
    def should_mention_user(cls) -> bool:
        """Проверить, стоит ли упоминать пользователя."""
        return random.random() < cls.MENTION_CHANCE

    @classmethod
    def get_category_for_event(cls, event_type: str) -> str:
        """
        Получить категорию сообщения для типа события.

        Args:
            event_type: Тип события (earn, lose, business_buy, lottery_win, etc.)

        Returns:
            Категория сообщения
        """
        event_map = {
            "earn": "money",
            "lose": "risk",
            "business_buy": "business",
            "business_upgrade": "business",
            "lottery_win": "lottery",
            "lottery_lose": "lottery",
            "jackpot_win": "jackpot",
            "credit_take": "risk",
            "credit_repay": "money",
            "bankrupt": "risk",
            "chat_level_up": "achievements",
        }
        return event_map.get(event_type, "money")

    @classmethod
    def is_chat_silent(cls, last_activity_time: Optional[datetime]) -> bool:
        """
        Проверить, затих ли чат.

        Args:
            last_activity_time: Время последней активности

        Returns:
            True если чат не активен более SILENT_THRESHOLD_MINUTES
        """
        if not last_activity_time:
            return True

        silent_threshold = timedelta(minutes=cls.SILENT_THRESHOLD_MINUTES)
        return datetime.now() - last_activity_time > silent_threshold

    @classmethod
    def get_random_category(cls) -> str:
        """Получить случайную категорию сообщения."""
        categories = list(MESSAGES.keys())
        return random.choice(categories)

    @classmethod
    def get_market_message(cls, resource: str, price_change: float) -> str:
        """
        Сгенерировать сообщение об изменении цен на рынке.

        Args:
            resource: Тип ресурса
            price_change: Изменение цены в процентах

        Returns:
            Текст сообщения
        """
        resource_names = {
            "lemons": "🍋 Лимоны",
            "grain": "🌾 Зерно",
            "goods": "📦 Товары",
            "digital": "💾 Цифровые товары",
        }

        name = resource_names.get(resource, resource)

        if price_change > 0:
            return f"📈 {name} подорожали на {price_change:.1f}%! Успейте продать!"
        elif price_change < 0:
            return f"📉 {name} подешевели на {abs(price_change):.1f}%! Покупайте!"
        else:
            return f"📊 Цены на {name} не изменились."

    @classmethod
    def get_jackpot_message(cls, jackpot_amount: float, time_until_draw: str) -> str:
        """
        Сгенерировать сообщение о джекпоте.

        Args:
            jackpot_amount: Размер банка
            time_until_draw: Время до розыгрыша

        Returns:
            Текст сообщения
        """
        if jackpot_amount < 100:
            return f"🎰 Джекпот растёт! Сейчас ${jackpot_amount:.0f}"
        elif jackpot_amount < 500:
            return f"🔥 Джекпот уже ${jackpot_amount:.0f}! Кто заберёт?"
        else:
            return f"🚨 МЕГА ДЖЕКПОТ ${jackpot_amount:.0f}! Розыгрыш через {time_until_draw}!"

    @classmethod
    def get_level_up_message(cls, new_level: int, energy_bonus: int) -> str:
        """
        Сгенерировать сообщение о повышении уровня чата.

        Args:
            new_level: Новый уровень
            energy_bonus: Бонус энергии для участников

        Returns:
            Текст сообщения
        """
        bonuses = []
        if new_level >= 2:
            bonuses.append("+5% к доходу")
        if new_level >= 3:
            bonuses.append("1 бесплатный билет джекпота")
        if new_level >= 4:
            bonuses.append("-10% к расходу энергии")
        if new_level >= 5:
            bonuses.append("+10% шанс джекпота")

        bonus_text = ", ".join(bonuses) if bonuses else "новые бонусы"

        return (
            f"🏆 Чат достиг уровня {new_level}!\n\n"
            f"🎁 Бонусы: {bonus_text}\n"
            f"⚡ +{energy_bonus} энергии всем участникам!"
        )


class ChatActivityTracker:
    """
    Трекер активности чатов.
    Хранит состояние активности для каждого чата.
    """

    def __init__(self):
        # chat_id -> последняя активность
        self._last_activity: Dict[int, datetime] = {}
        # chat_id -> последнее сообщение
        self._last_message: Dict[int, datetime] = {}
        # chat_id -> список активных пользователей
        self._active_users: Dict[int, List[int]] = {}

    def record_activity(self, chat_id: int, user_id: Optional[int] = None):
        """Записать активность в чате."""
        self._last_activity[chat_id] = datetime.now()

        if user_id:
            if chat_id not in self._active_users:
                self._active_users[chat_id] = []
            if user_id not in self._active_users[chat_id]:
                self._active_users[chat_id].append(user_id)
            # Держим только последних 10 пользователей
            if len(self._active_users[chat_id]) > 10:
                self._active_users[chat_id] = self._active_users[chat_id][-10:]

    def record_message(self, chat_id: int):
        """Записать отправку сообщения в чат."""
        self._last_message[chat_id] = datetime.now()

    def get_last_activity(self, chat_id: int) -> Optional[datetime]:
        """Получить время последней активности."""
        return self._last_activity.get(chat_id)

    def get_last_message_time(self, chat_id: int) -> Optional[datetime]:
        """Получить время последнего сообщения."""
        return self._last_message.get(chat_id)

    def get_active_users(self, chat_id: int) -> List[int]:
        """Получить список активных пользователей."""
        return self._active_users.get(chat_id, [])

    def is_chat_silent(self, chat_id: int) -> bool:
        """Проверить, затих ли чат."""
        last_activity = self.get_last_activity(chat_id)
        return ActivityService.is_chat_silent(last_activity)


# Глобальный трекер активности
activity_tracker = ChatActivityTracker()
