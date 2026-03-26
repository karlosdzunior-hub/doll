"""
Утилиты и вспомогательные функции
Содержит генерацию событий, форматирование, проверки
"""

import random
from datetime import datetime, date
from typing import Tuple, Optional
from config import config
from db import db


class EventGenerator:
    """Генератор случайных событий"""

    @staticmethod
    def get_random_event() -> Tuple[str, str, float]:
        """
        Генерирует случайное событие
        Returns: (event_key, event_name, effect_value)
        """
        events_weights = {
            "fire": 20,  # Пожар - урон
            "tax": 25,  # Налог - урон
            "bonus": 30,  # Бонус - награда
            "found": 25,  # Находка - награда
        }

        # Выбираем событие по весам
        event_key = random.choices(
            list(events_weights.keys()), weights=list(events_weights.values())
        )[0]

        event_config = config.EVENTS[event_key]

        if event_key in ["fire", "tax"]:
            # Негативное событие - урон
            effect = random.uniform(
                event_config[f"min_{'damage' if event_key == 'fire' else 'damage'}"],
                event_config[f"max_{'damage' if event_key == 'fire' else 'damage'}"],
            )
        else:
            # Позитивное событие - награда
            effect = random.uniform(
                event_config["min_bonus"], event_config["max_bonus"]
            )

        return event_key, event_config["name"], round(effect, 2)

    @staticmethod
    def is_negative_event(event_key: str) -> bool:
        """Проверяет, является ли событие негативным"""
        return event_key in ["fire", "tax"]

    @staticmethod
    def can_protect(user_id: int, event_key: str) -> Tuple[bool, str]:
        """
        Проверяет, может ли игрок защититься от события
        Returns: (can_protect, reason)
        """
        if EventGenerator.is_negative_event(event_key):
            # VIP защищает от всех негативных событий
            if db.check_vip(user_id):
                return True, "🛡️ VIP защита активна!"

            # Щит защищает от одного негативного события
            shield_count = db.get_resource(user_id, "shield")
            if shield_count > 0:
                return True, "🛡️ У вас есть щит!"

            return False, "Нет защиты"

        return False, "Событие позитивное"


class GameLogic:
    """Основная игровая логика"""

    @staticmethod
    def process_daily_event(user_id: int) -> dict:
        """
        Обрабатывает ежедневное событие для пользователя
        Returns: словарь с результатом события
        """
        today = date.today().isoformat()
        last_event = db.get_last_event_date(user_id)

        # Проверяем, было ли уже событие сегодня
        if last_event == today:
            return {
                "processed": False,
                "message": "⏰ Событие уже обработано сегодня. Приходите завтра!",
            }

        # Генерируем событие
        event_key, event_name, effect = EventGenerator.get_random_event()

        # Проверяем защиту
        can_protect, protect_reason = EventGenerator.can_protect(user_id, event_key)

        result = {
            "processed": True,
            "event_key": event_key,
            "event_name": event_name,
            "effect": effect,
            "protected": False,
            "message": "",
        }

        if EventGenerator.is_negative_event(event_key) and can_protect:
            # Защищаем от негативного события
            result["protected"] = True

            # Используем щит если есть (VIP не тратит щит)
            if not db.check_vip(user_id):
                db.use_resource(user_id, "shield")

            result["message"] = (
                f"{event_name}\n\n{protect_reason}\n✅ Урон заблокирован!"
            )
        else:
            # Применяем эффект события
            if EventGenerator.is_negative_event(event_key):
                db.update_balance(user_id, -effect)
                result["message"] = f"{event_name}\n\n💸 Вы потеряли ${effect}!"
            else:
                db.update_balance(user_id, effect)
                result["message"] = f"{event_name}\n\n💰 Вы получили ${effect}!"

        # Логируем событие
        db.log_event(user_id, event_key, effect)
        db.set_last_event_date(user_id, today)

        # VIP бонус
        if db.check_vip(user_id):
            db.update_balance(user_id, config.VIP_DAILY_BONUS)
            result["message"] += f"\n\n⭐ VIP бонус: +${config.VIP_DAILY_BONUS}"

        return result

    @staticmethod
    def get_upgrade_cost(business_id: int) -> float:
        """Рассчитать стоимость апгрейда бизнеса"""
        business = db.get_business(business_id)
        if not business:
            return 0

        biz_config = config.BUSINESS_TYPES[business["business_type"]]
        new_level = business["level"] + 1

        return round(
            business["base_income"]
            * (biz_config["upgrade_cost_multiplier"] ** (new_level - 1)),
            2,
        )

    @staticmethod
    def play_lottery(user_id: int) -> dict:
        """
        Игра в лотерею
        Returns: результат лотереи
        """
        cost = config.LOTTERY_COST_STARS

        # Списываем стоимость (в реальности - Stars)
        # Здесь просто уменьшаем баланс для демо
        if db.get_balance(user_id) < cost:
            return {
                "won": False,
                "win_amount": 0,
                "message": f"Недостаточно средств! Нужно ${cost}",
            }

        db.update_balance(user_id, -cost)

        # Шанс на победу
        if random.random() < config.LOTTERY_WIN_CHANCE:
            win_amount = round(
                random.uniform(config.LOTTERY_MIN_WIN, config.LOTTERY_MAX_WIN), 2
            )
            db.update_balance(user_id, win_amount)
            return {
                "won": True,
                "win_amount": win_amount,
                "message": f"🎉 ПОБЕДА! Вы выиграли ${win_amount}!",
            }

        return {
            "won": False,
            "win_amount": 0,
            "message": "😢 К сожалению, вы не выиграли. Попробуйте ещё раз!",
        }


class Formatter:
    """Форматирование сообщений"""

    @staticmethod
    def format_balance(user_id: int) -> str:
        """Форматирует информацию о балансе"""
        user = db.get_user(user_id)
        if not user:
            return "❌ Пользователь не найден"

        balance = user["balance"]
        vip_status = "⭐ VIP" if db.check_vip(user_id) else "Базовый"

        # Получаем бизнесы
        businesses = db.get_user_businesses(user_id)

        msg = f"""💰 Ваш баланс: ${balance:.2f}
📊 Статус: {vip_status}
🏢 Бизнесов: {len(businesses)}

"""

        if businesses:
            msg += "📋 Ваши бизнесы:\n"
            for biz in businesses:
                income = db.get_business_income(biz["id"])
                msg += (
                    f"   • {biz['name']} (Ур. {biz['level']}) - ${income:.2f}/событие\n"
                )

        # Ресурсы
        resources = db.get_all_resources(user_id)
        if resources:
            msg += "\n🎒 Ресурсы:\n"
            for res_type, quantity in resources.items():
                res_name = {"shield": "🛡️ Щит", "lottery_ticket": "🎫 Билет"}.get(
                    res_type, res_type
                )
                msg += f"   {res_name}: {quantity}\n"

        return msg

    @staticmethod
    def format_businesses(user_id: int) -> str:
        """Форматирует список бизнесов с кнопками"""
        businesses = db.get_user_businesses(user_id)

        if not businesses:
            return "📭 У вас пока нет бизнесов.\nСоздайте свой первый бизнес!"

        msg = "🏢 Ваши бизнесы:\n\n"

        for i, biz in enumerate(businesses, 1):
            income = db.get_business_income(biz["id"])
            upgrade_cost = GameLogic.get_upgrade_cost(biz["id"])
            msg += f"{i}. {biz['name']}\n"
            msg += f"   Уровень: {biz['level']}\n"
            msg += f"   Доход: ${income:.2f}/событие\n"
            msg += f"   Апгрейд: ${upgrade_cost:.2f}\n\n"

        return msg

    @staticmethod
    def format_leaderboard() -> str:
        """Форматирует лидерборд"""
        leaders = db.get_leaderboard(10)

        if not leaders:
            return "🏆 Лидерборд пуст"

        msg = "🏆 ТОП-10 ИГРОКОВ:\n\n"

        medals = ["🥇", "🥈", "🥉"]

        for i, player in enumerate(leaders, 1):
            medal = medals[i - 1] if i <= 3 else f"{i}."
            username = player["username"] or f"User{player['user_id']}"
            msg += f"{medal} {username} - ${player['balance']:.2f}\n"

        return msg

    @staticmethod
    def format_referrals(user_id: int) -> str:
        """Форматирует информацию о рефералах"""
        referrals = db.get_referrals(user_id)
        count = len(referrals)
        total_bonus = sum(r["bonus_given"] for r in referrals)

        msg = f"""🔁 Реферальная программа

👥 Приглашено друзей: {count}
💰 Заработано на рефералах: ${total_bonus:.2f}

🎁 Бонус за приглашение: ${config.REFERRAL_BONUS:.2f}

📎 Ваша реферальная ссылка:
https://t.me/{config.BOT_USERNAME}?start={user_id}

"""

        if referrals:
            msg += "📋 Список рефералов:\n"
            for ref in referrals:
                username = ref["username"] or f"User{ref['referred_user_id']}"
                msg += f"   • {username} (+${ref['bonus_given']:.2f})\n"

        return msg


# Глобальные экземпляры
event_gen = EventGenerator()
game_logic = GameLogic()
formatter = Formatter()
