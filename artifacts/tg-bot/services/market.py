"""
Сервис рынка - динамические цены и NPC торговля
"""

import random
from datetime import datetime
from db import db
from config import config


class MarketService:
    """
    Система рынка:
    - Цены зависят от спроса/предложения
    - NPC-маркетмейкер стабилизирует рынок
    - Каждые 5 минут обновление
    """

    @staticmethod
    def process_market_tick() -> dict:
        """
        Обработка тика рынка (каждые 5 минут)
        NPC покупает/продаёт для стабилизации
        """
        stats = {
            "resources_updated": 0,
            "npc_trades": 0,
            "total_npc_volume": 0,
        }

        prices = db.get_market_prices()

        for resource_type, data in prices.items():
            base = data["base_price"]
            current = data["current_price"]

            # NPC логика:
            # - Покупает если цена < базовой (дешёво)
            # - Продаёт если цена > базовой (дорого)

            trade_amount = 0

            if current < base:
                # Цена низкая - NPC покупает
                trade_amount = random.randint(
                    config.NPC_MIN_TRADE, config.NPC_MAX_TRADE
                )
                db.update_market_price(resource_type, demand_delta=trade_amount)
                stats["npc_trades"] += 1
                stats["total_npc_volume"] += trade_amount

            elif current > base:
                # Цена высокая - NPC продаёт
                trade_amount = random.randint(
                    config.NPC_MIN_TRADE, config.NPC_MAX_TRADE
                )
                db.update_market_price(resource_type, supply_delta=trade_amount)
                stats["npc_trades"] += 1
                stats["total_npc_volume"] += trade_amount

            stats["resources_updated"] += 1

        return stats

    @staticmethod
    def get_market_overview() -> str:
        """Получить обзор рынка"""
        prices = db.get_market_prices()

        msg = "📊 <b>Рынок</b>\n\n"

        for resource_type, data in prices.items():
            res_info = config.RESOURCES.get(resource_type, {})
            name = res_info.get("name", resource_type)
            current = data["current_price"]
            base = data["base_price"]

            # Индикатор тренда
            if current > base * 1.2:
                trend = "📈"
            elif current < base * 0.8:
                trend = "📉"
            else:
                trend = "➖"

            # Цвет
            if current > base:
                color = "🔴"
            elif current < base:
                color = "🟢"
            else:
                color = "⚪"

            msg += f"{color} {name}\n"
            msg += f"   💰 ${current:.2f} {trend}\n"
            msg += f"   📌 Базовая: ${base:.2f}\n\n"

        return msg

    @staticmethod
    def apply_event_multiplier(resource_type: str, multiplier: float):
        """Применить множитель события к ресурсу"""
        prices = db.get_market_prices()
        if resource_type in prices:
            new_price = prices[resource_type]["current_price"] * multiplier
            base = prices[resource_type]["base_price"]
            new_price = max(
                base * config.MIN_PRICE_MULTIPLIER,
                min(base * config.MAX_PRICE_MULTIPLIER, new_price),
            )

            with db.get_connection() as conn:
                conn.cursor().execute(
                    "UPDATE market_prices SET current_price = ? WHERE resource_type = ?",
                    (new_price, resource_type),
                )
