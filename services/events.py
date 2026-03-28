"""
Сервис событий - глобальные рыночные события
"""

import random
from db import db
from config import config
from services.market import MarketService


class EventService:
    """
    Система рыночных событий:
    - Каждые 1-2 часа случайное событие
    - Влияет на цены ресурсов
    - Уведомляет всех активных игроков
    """

    EVENTS = {
        "grain_demand": {
            "name": "📈 Спрос на зерно вырос",
            "market_multiplier": 1.3,
            "affected_resource": "grain",
            "message": "📈 Спрос на зерно вырос! Цены +30%",
        },
        "crisis": {
            "name": "📉 Экономический кризис",
            "market_multiplier": 0.8,
            "affected_resource": "all",
            "message": "📉 Кризис! Все ресурсы дешевеют -20%",
        },
        "digital_boom": {
            "name": "🚀 Цифровой бум",
            "market_multiplier": 2.0,
            "affected_resource": "digital",
            "message": "🚀 Бум цифровых товаров! Цены x2",
        },
        "lemon_harvest": {
            "name": "🍋 Урожай лимонов",
            "market_multiplier": 0.75,
            "affected_resource": "lemons",
            "message": "🍋 Отличный урожай лимонов! Цены упали -25%",
        },
        "goods_shortage": {
            "name": "📦 Дефицит товаров",
            "market_multiplier": 1.5,
            "affected_resource": "goods",
            "message": "📦 Дефицит товаров! Цены +50%",
        },
        "market_boom": {
            "name": "💰 Рыночный бум",
            "market_multiplier": 1.5,
            "affected_resource": "random",
            "message": "💰 Бум! Один случайный ресурс x1.5",
        },
    }

    @staticmethod
    def trigger_random_event() -> dict:
        """Запустить случайное глобальное событие"""
        event_key = random.choice(list(EventService.EVENTS.keys()))
        event = EventService.EVENTS[event_key]
        affected = event["affected_resource"]

        if affected == "all":
            for res_type in config.RESOURCES.keys():
                MarketService.apply_event_multiplier(res_type, event["market_multiplier"])
        elif affected == "random":
            res_type = random.choice(list(config.RESOURCES.keys()))
            MarketService.apply_event_multiplier(res_type, event["market_multiplier"])
            affected = res_type
        else:
            MarketService.apply_event_multiplier(affected, event["market_multiplier"])

        try:
            db.add_global_event(
                event_type=event_key,
                multiplier=event["market_multiplier"],
                affected_resource=affected,
                message=event["message"],
                hours=random.randint(1, 3),
            )
        except Exception:
            pass

        return {
            "name": event["name"],
            "message": event["message"],
            "affected": affected,
        }

    @staticmethod
    def get_active_events_list() -> list:
        """Список активных событий"""
        try:
            events = db.get_active_events()
            result = []
            for event in events:
                event_info = EventService.EVENTS.get(event["event_type"], {})
                result.append({
                    "name": event_info.get("name", event["event_type"]),
                    "message": event.get("message", ""),
                })
            return result
        except Exception:
            return []

    @staticmethod
    def check_user_protection(user_id: int) -> tuple:
        if db.check_vip(user_id):
            return True, "⭐ VIP защита"
        try:
            if db.get_item(user_id, "shield") > 0:
                return True, "🛡️ Щит"
        except Exception:
            pass
        return False, None
