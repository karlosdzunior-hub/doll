"""
Production конфигурация бота "Микрокапитализм: Жизнь на 1 доллар"
"""

import os
from dataclasses import dataclass, field
from typing import Dict


@dataclass
class BotConfig:
    # Telegram
    TOKEN: str = os.getenv("BOT_TOKEN", "YOUR_TOKEN_HERE")
    ADMIN_IDS: list = field(default_factory=lambda: [int(os.getenv("ADMIN_ID", "0"))])
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///game.db")

    # Игрок
    STARTING_BALANCE: float = 1.0

    # ==================== РЕСУРСЫ ====================
    RESOURCES: Dict[str, dict] = field(
        default_factory=lambda: {
            "food": {"name": "🍎 Еда", "base_price": 10.0},
            "materials": {"name": "🔧 Материалы", "base_price": 20.0},
            "energy": {"name": "⚡ Энергия", "base_price": 15.0},
            "tech": {"name": "💻 Технологии", "base_price": 50.0},
            "crypto": {"name": "🪙 Крипто", "base_price": 100.0},
        }
    )

    RESOURCE_MAX: int = 1000  # Лимит ресурсов на тип

    # ==================== ЭНЕРГИЯ ====================
    MAX_ENERGY: int = 100  # Максимальная энергия
    MIN_ENERGY_TO_WORK: int = 10  # Порог для работы бизнесов
    BASE_REGEN_RATE: int = 1  # +1 энергия каждые REGEN_INTERVAL секунд
    REGEN_INTERVAL: int = 600  # 10 минут

    # ==================== БИЗНЕСЫ ====================
    BUSINESSES: Dict[str, dict] = field(
        default_factory=lambda: {
            "lemonade": {
                "name": "🍋 Лимонадная",
                "resource": "food",
                "production_rate": 1.0,
                "base_cost": 1.0,
                "energy_cost": 1,  # энергия/час
            },
            "farm": {
                "name": "🌾 Ферма",
                "resource": "food",
                "production_rate": 3.0,
                "base_cost": 20.0,
                "energy_cost": 2,
            },
            "factory": {
                "name": "🏭 Завод",
                "resource": "materials",
                "production_rate": 5.0,
                "base_cost": 50.0,
                "energy_cost": 3,
            },
            "power_plant": {
                "name": "⚡ Электростанция",
                "resource": "energy",
                "production_rate": 5.0,  # Производит энергию для продажи
                "base_cost": 40.0,
                "energy_cost": 0,  # Не потребляет
                "energy_gen": 5,  # Генерирует энергию
            },
            "it_company": {
                "name": "💻 IT-компания",
                "resource": "tech",
                "production_rate": 2.0,
                "base_cost": 100.0,
                "energy_cost": 2,
            },
            "crypto_farm": {
                "name": "🪙 Крипто-ферма",
                "resource": "crypto",
                "production_rate": 1.0,
                "base_cost": 200.0,
                "energy_cost": 5,
            },
        }
    )

    # ==================== РЫНОК ====================
    PRICE_UPDATE_INTERVAL: int = 300  # 5 минут
    MIN_PRICE_MULTIPLIER: float = 0.5
    MAX_PRICE_MULTIPLIER: float = 3.0
    MARKET_FEE: float = 0.05  # 5% комиссия

    # NPC настройки
    NPC_MIN_TRADE: int = 5  # мин количество для NPC
    NPC_MAX_TRADE: int = 20  # макс количество для NPC

    # ==================== ПЕРЕВОДЫ ====================
    TRANSFER_FEE: float = 0.03  # 3% комиссия

    # ==================== VIP ====================
    VIP_COST_STARS: int = 50
    VIP_DURATION_DAYS: int = 7
    VIP_PRODUCTION_BONUS: float = 0.20  # +20% к производству
    VIP_ENERGY_DISCOUNT: float = 0.30  # -30% к расходу энергии

    # ==================== ДОНАТ (Stars) ====================
    ENERGY_20_COST: int = 5  # +20 энергии
    ENERGY_50_COST: int = 10  # +50 энергии
    BOOST_1H_COST: int = 10  # x2 на 1 час
    SHIELD_COST: int = 5
    INSIDER_COST: int = 15  # узнать событие
    MARKET_BOOST_COST: int = 20

    # ==================== РЕФЕРАЛЫ ====================
    REFERRAL_BONUS: float = 5.0

    # ==================== ФОНовые ЗАДАЧИ ====================
    TICK_INTERVAL: int = 300  # 5 минут


config = BotConfig()
