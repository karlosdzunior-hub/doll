"""
Production конфигурация бота "Микрокапитализм: Жизнь на 1 доллар"
v2.0 — балансированная экономика, джекпот, кредиты, удержание
"""

import os
from dataclasses import dataclass, field
from typing import Dict


@dataclass
class BotConfig:
    # Telegram
    TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", os.getenv("BOT_TOKEN", "YOUR_TOKEN_HERE"))
    ADMIN_IDS: list = field(default_factory=lambda: [int(os.getenv("ADMIN_ID", "0"))])
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///game.db")

    # ==================== СТАРТОВЫЕ ДАННЫЕ ====================
    STARTING_BALANCE: float = 100.0       # $100 стартовый баланс
    STARTING_ENERGY: int = 20             # 20 энергии стартовой
    STARTING_TICKETS: int = 1             # 1 билет джекпота

    # ==================== РЕСУРСЫ ====================
    RESOURCES: Dict[str, dict] = field(
        default_factory=lambda: {
            "food":      {"name": "🍎 Еда",         "base_price": 10.0},
            "materials": {"name": "🔧 Материалы",   "base_price": 20.0},
            "tech":      {"name": "💻 Технологии",  "base_price": 50.0},
            "crypto":    {"name": "🪙 Крипто",       "base_price": 100.0},
        }
    )
    RESOURCE_MAX: int = 1000

    # ==================== ЭНЕРГИЯ ====================
    MAX_ENERGY: int = 100
    MIN_ENERGY_TO_WORK: int = 10
    BASE_REGEN_RATE: int = 1        # +1 энергия каждые 10 мин
    REGEN_INTERVAL: int = 600       # 10 минут в секундах

    # ==================== БИЗНЕСЫ (БАЛАНСИРОВАННЫЕ) ====================
    BUSINESSES: Dict[str, dict] = field(
        default_factory=lambda: {
            "lemonade": {
                "name":           "🍋 Лимонадная",
                "resource":       "food",
                "income_per_hour": 5.0,     # $5/час
                "base_cost":      50.0,      # цена: $50
                "energy_cost":    1,         # 1 энергия/час
            },
            "farm": {
                "name":           "🌾 Ферма",
                "resource":       "food",
                "income_per_hour": 15.0,    # $15/час
                "base_cost":      200.0,    # цена: $200
                "energy_cost":    2,        # 2 энергии/час
            },
            "factory": {
                "name":           "🏭 Завод",
                "resource":       "materials",
                "income_per_hour": 50.0,   # $50/час
                "base_cost":      600.0,   # цена: $600
                "energy_cost":    5,       # 5 энергии/час
            },
            "it_company": {
                "name":           "💻 IT-бизнес",
                "resource":       "tech",
                "income_per_hour": 120.0,  # $120/час
                "base_cost":      1500.0,  # цена: $1500
                "energy_cost":    8,       # 8 энергии/час
            },
            "crypto_farm": {
                "name":           "🪙 Крипто-ферма",
                "resource":       "crypto",
                "income_per_hour": 250.0,  # $250/час
                "base_cost":      3000.0,  # цена: $3000
                "energy_cost":    15,      # 15 энергии/час
            },
        }
    )

    # ==================== РЫНОК ====================
    PRICE_UPDATE_INTERVAL: int = 300
    MIN_PRICE_MULTIPLIER: float = 0.5
    MAX_PRICE_MULTIPLIER: float = 3.0
    MARKET_FEE: float = 0.05

    # ==================== ПЕРЕВОДЫ ====================
    TRANSFER_FEE: float = 0.02        # 2% комиссия

    # ==================== VIP ====================
    VIP_COST_STARS: int = 50
    VIP_DURATION_DAYS: int = 7
    VIP_PRODUCTION_BONUS: float = 0.20
    VIP_ENERGY_DISCOUNT: float = 0.30

    # ==================== ДОНАТ (TELEGRAM STARS) ====================
    # Энергия
    ENERGY_20_COST: int = 5    # +20 энергии → 5⭐
    ENERGY_50_COST: int = 10   # +50 энергии → 10⭐

    # Деньги
    MONEY_200_COST: int = 5    # +$200 → 5⭐
    MONEY_500_COST: int = 10   # +$500 → 10⭐

    # Билеты джекпота
    TICKET_1_COST: int = 3     # 1 билет → 3⭐
    TICKET_5_COST: int = 10    # 5 билетов → 10⭐

    # Прочее
    BOOST_1H_COST: int = 10
    SHIELD_COST: int = 5

    # ==================== РЕФЕРАЛЫ ====================
    REFERRAL_BONUS: float = 5.0

    # ==================== ЛОТЕРЕЯ ====================
    LOTTERY_COST: float = 10.0
    LOTTERY_CHANCES: dict = field(
        default_factory=lambda: {
            0:   0.70,   # 70% проигрыш
            1.5: 0.25,   # 25% x1.5
            3:   0.04,   # 4% x3
            10:  0.01,   # 1% x10
        }
    )

    # ==================== ДЖЕКПОТ ====================
    JACKPOT_TICKET_COST: float = 10.0   # $10 за билет
    JACKPOT_BANK_SHARE: float = 0.50    # 50% → в банк джекпота
    JACKPOT_BURN_SHARE: float = 0.30    # 30% → сжигание
    JACKPOT_SYSTEM_SHARE: float = 0.20  # 20% → система
    JACKPOT_INTERVAL_HOURS: int = 6     # розыгрыш каждые 6 часов

    # Гарантированный первый выигрыш (онбординг)
    JACKPOT_FIRST_WIN_MULTIPLIER: float = 1.5

    # ==================== КРЕДИТЫ ====================
    CREDITS: dict = field(
        default_factory=lambda: {
            "small": {
                "name":      "💵 Малый кредит",
                "amount":    200.0,
                "repay":     260.0,
                "hours":     12,
            },
            "medium": {
                "name":      "💰 Средний кредит",
                "amount":    500.0,
                "repay":     700.0,
                "hours":     24,
            },
            "large": {
                "name":      "🏦 Большой кредит",
                "amount":    1000.0,
                "repay":     1500.0,
                "hours":     48,
            },
        }
    )
    CREDIT_HOURLY_INTEREST: float = 0.02   # 2% в час пени за просрочку

    # ==================== БАНКРОТСТВО ====================
    BANKRUPTCY_DEBT_FORGIVE: float = 0.30  # списать 30% долга при банкротстве

    # ==================== ФОНОВЫЕ ЗАДАЧИ ====================
    TICK_INTERVAL: int = 300      # 5 минут
    DEBT_CHECK_INTERVAL: int = 3600  # проверка долгов каждый час

    # ==================== ЛИМИТЫ ====================
    DAILY_TRANSFER_LIMIT: float = 1000.0

    # ==================== ЧАТЫ ====================
    XP_PER_COMMAND: int = 1
    XP_PER_TRANSFER: int = 2
    XP_PER_LOTTERY: int = 5
    XP_PER_NEW_USER: int = 10
    CHAT_LEVEL_UP_ENERGY_BONUS: int = 10
    ADD_BOT_ENERGY_BONUS: int = 5
    ADD_BOT_LOTTERY_TICKET: int = 1

    # ==================== ПЛАТЕЖИ STARS ====================
    PAYMENT_ITEMS: dict = field(
        default_factory=lambda: {
            "energy_20":  {"name": "⚡ +20 Энергии",        "stars": 5},
            "energy_50":  {"name": "🔥 +50 Энергии",        "stars": 10},
            "money_200":  {"name": "💵 +$200",              "stars": 5},
            "money_500":  {"name": "💰 +$500",              "stars": 10},
            "ticket_1":   {"name": "🎫 1 билет джекпота",   "stars": 3},
            "ticket_5":   {"name": "🎫 5 билетов джекпота", "stars": 10},
            "boost_1h":   {"name": "⚡ Буст x2 (1 час)",    "stars": 10},
            "shield":     {"name": "🛡️ Щит",                "stars": 5},
            "lottery_premium": {"name": "🎰 Лотерея Премиум","stars": 2},
            "vip_week":   {"name": "⭐ VIP (7 дней)",        "stars": 50},
        }
    )


config = BotConfig()
