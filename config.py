"""
Конфигурация бота
Содержит настройки для Telegram бота и игровые параметры
"""

import os
from dataclasses import dataclass


@dataclass
class BotConfig:
    TOKEN: str = os.getenv("BOT_TOKEN", "8007267591:AAGj655whQL82O1MoxC9FKiYzuJVohy6Qys")
    ADMIN_ID: int = int(os.getenv("ADMIN_ID", "0"))
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///game.db")

    STARTING_BALANCE: float = 1.0
    FIRST_BUSINESS_COST: float = 1.0

    BUSINESS_TYPES = {
        "lemonade": {
            "name": "Лимонадная 🍋",
            "base_income": 1.0,
            "base_cost": 1.0,
            "upgrade_cost_multiplier": 1.5,
        },
        "farm": {
            "name": "Ферма 🌾",
            "base_income": 2.0,
            "base_cost": 5.0,
            "upgrade_cost_multiplier": 1.8,
        },
    }

    EVENTS = {
        "fire": {"name": "Пожар 🔥", "min_damage": 1, "max_damage": 5},
        "tax": {"name": "Налог 📋", "min_damage": 1, "max_damage": 3},
        "bonus": {"name": "Бонус 🎁", "min_bonus": 2, "max_bonus": 10},
        "found": {"name": "Находка 💰", "min_bonus": 1, "max_bonus": 5},
    }

    VIP_COST_STARS: int = 5
    VIP_DAILY_BONUS: float = 5.0
    VIP_DURATION_DAYS: int = 7

    INSTANT_UPGRADE_COST_STARS: int = 3
    SHIELD_COST_STARS: int = 2
    LOTTERY_COST_STARS: int = 1

    LOTTERY_MIN_WIN: float = 5.0
    LOTTERY_MAX_WIN: float = 50.0
    LOTTERY_WIN_CHANCE: float = 0.3

    REFERRAL_BONUS: float = 2.0


config = BotConfig()
