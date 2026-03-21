"""
Сервис событий - глобальные и игровые события
"""

import random
from datetime import datetime, timedelta
from db import db
from config import config
from services.market import MarketService


class EventService:
    """
    Система событий:
    - Глобальные события влияют на рынок
    - Персональные события для игроков
    - Защита от событий через щиты/VIP
    """

    EVENTS = {
        "drought": {
            "name": "Засуха 🌵",
            "market_multiplier": 2.0,  # еда дорожает
            "affected_resource": "food",
            "message": "Засуха обрушилась на рынок! Цены на еду растут!",
        },
        "crisis": {
            "name": "Экономический кризис 📉",
            "market_multiplier": 0.7,  # все дешевеет
            "affected_resource": "all",
            "message": "Кризис! Все ресурсы падают в цене!",
        },
        "tech_boom": {
            "name": "Технологический бум 🚀",
            "market_multiplier": 1.5,
            "affected_resource": "tech",
            "message": "Бум технологий! Цены на технологии растут!",
        },
        "energy_shortage": {
            "name": "Энергетический кризис ⚡",
            "market_multiplier": 2.0,
            "affected_resource": "energy",
            "message": "Нехватка энергии! Цены на энергию взлетели!",
        },
        "crypto_rally": {
            "name": "Крипто-ралли 🚀🪙",
            "market_multiplier": 1.8,
            "affected_resource": "crypto",
            "message": "Крипто-ралли! Криптовалюта растёт!",
        },
        "building_boom": {
            "name": "Строительный бум 🏗️",
            "market_multiplier": 1.5,
            "affected_resource": "materials",
            "message": "Строительный бум! Материалы в цене!",
        },
    }

    @staticmethod
    def trigger_random_event() -> dict:
        """Запустить случайное глобальное событие"""
        event_key = random.choice(list(EventService.EVENTS.keys()))
        event = EventService.EVENTS[event_key]

        # Применяем к рынку
        if event["affected_resource"] == "all":
            for res_type in config.RESOURCES.keys():
                MarketService.apply_event_multiplier(
                    res_type, event["market_multiplier"]
                )
        else:
            MarketService.apply_event_multiplier(
                event["affected_resource"], event["market_multiplier"]
            )

        # Записываем в БД
        db.add_global_event(
            event_type=event_key,
            multiplier=event["market_multiplier"],
            affected_resource=event["affected_resource"],
            message=event["message"],
            hours=random.randint(12, 48),
        )

        return {
            "name": event["name"],
            "message": event["message"],
            "duration_hours": 24,
        }

    @staticmethod
    def get_active_events_list() -> list:
        """Получить список активных событий"""
        events = db.get_active_events()
        result = []

        for event in events:
            event_info = EventService.EVENTS.get(event["event_type"], {})
            result.append(
                {
                    "name": event_info.get("name", event["event_type"]),
                    "message": event["message"],
                    "ends_at": event["ends_at"],
                }
            )

        return result

    @staticmethod
    def get_next_event_preview() -> str:
        """Предпросмотр следующего события (для Insider)"""
        # Случайное событие
        event_key = random.choice(list(EventService.EVENTS.keys()))
        event = EventService.EVENTS[event_key]

        return f"""🔮 <b>Инсайдерская информация</b>

📌 Следующее событие: <b>{event["name"]}</b>

💡 {event["message"]}

⏱️ Появится в ближайшее время!"""

    @staticmethod
    def check_user_protection(user_id: int) -> tuple:
        """
        Проверяет защищён ли игрок от событий
        Returns: (is_protected, reason)
        """
        # VIP защищён
        if db.check_vip(user_id):
            return True, "⭐ VIP защита"

        # Щит
        if db.get_item(user_id, "shield") > 0:
            return True, "🛡️ Щит"

        return False, None

    @staticmethod
    def use_protection(user_id: int) -> bool:
        """Использовать защиту (если есть)"""
        if db.check_vip(user_id):
            return False  # VIP не тратит щит

        if db.get_item(user_id, "shield") > 0:
            db.use_item(user_id, "shield")
            return True

        return False
