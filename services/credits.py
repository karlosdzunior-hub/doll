"""
Сервис кредитов — займы с процентами, давление долга
"""

from datetime import datetime, timedelta
from typing import Dict, Optional

from config import config


class CreditService:

    @staticmethod
    def get_available_credits() -> Dict:
        """Список доступных кредитов"""
        return config.CREDITS

    @staticmethod
    def take_credit(db, user_id: int, credit_type: str) -> Dict:
        """Взять кредит"""
        if credit_type not in config.CREDITS:
            return {"success": False, "error": "Неизвестный тип кредита"}

        # Проверяем нет ли уже активного кредита
        active = db.get_active_credit(user_id)
        if active:
            remaining = active["repay_amount"] - active["paid_amount"]
            return {
                "success": False,
                "error": f"У вас уже есть кредит! Долг: ${remaining:.2f}"
            }

        credit = config.CREDITS[credit_type]
        amount = credit["amount"]
        repay = credit["repay"]
        hours = credit["hours"]

        due_time = datetime.now() + timedelta(hours=hours)

        db.update_balance(user_id, amount)
        db.create_credit(user_id, credit_type, amount, repay, due_time)
        db.log_action(user_id, "credit_taken", f"Взят {credit['name']}: +${amount}, долг: ${repay}")

        return {
            "success": True,
            "amount": amount,
            "repay": repay,
            "due_time": due_time,
            "message": (
                f"💳 <b>{credit['name']}</b>\n\n"
                f"✅ Получено: <b>+${amount:.0f}</b>\n"
                f"💸 Нужно вернуть: <b>${repay:.0f}</b>\n"
                f"⏰ Срок: {hours} часов\n"
                f"📅 Дедлайн: {due_time.strftime('%d.%m %H:%M')}\n\n"
                f"⚠️ При просрочке: +2% в час!"
            )
        }

    @staticmethod
    def repay_credit(db, user_id: int, amount: Optional[float] = None) -> Dict:
        """Погасить кредит (полностью или частично)"""
        active = db.get_active_credit(user_id)
        if not active:
            return {"success": False, "error": "У вас нет активных кредитов"}

        remaining = active["repay_amount"] - active["paid_amount"]
        balance = db.get_balance(user_id)

        if amount is None:
            amount = remaining  # Полное погашение

        if amount > balance:
            return {"success": False, "error": f"Недостаточно средств. Нужно ${amount:.2f}, у вас ${balance:.2f}"}

        amount = min(amount, remaining)

        db.update_balance(user_id, -amount)
        db.pay_credit(user_id, active["id"], amount)

        new_remaining = remaining - amount
        if new_remaining <= 0:
            db.close_credit(user_id, active["id"])
            db.log_action(user_id, "credit_repaid", f"Кредит закрыт")
            return {
                "success": True,
                "paid": amount,
                "remaining": 0,
                "closed": True,
                "message": (
                    f"✅ <b>Кредит погашен!</b>\n\n"
                    f"💰 Оплачено: ${amount:.2f}\n"
                    f"🎉 Долг закрыт!"
                )
            }

        return {
            "success": True,
            "paid": amount,
            "remaining": new_remaining,
            "closed": False,
            "message": (
                f"💳 <b>Частичная оплата</b>\n\n"
                f"💰 Оплачено: ${amount:.2f}\n"
                f"💸 Осталось: ${new_remaining:.2f}"
            )
        }

    @staticmethod
    def apply_interest(db) -> int:
        """
        Применить просроченные проценты — каждый час.
        Возвращает количество должников.
        """
        overdue = db.get_overdue_credits()
        count = 0

        for credit in overdue:
            user_id = credit["user_id"]
            debt = credit["repay_amount"] - credit["paid_amount"]
            interest = debt * config.CREDIT_HOURLY_INTEREST
            db.add_credit_debt(credit["id"], interest)
            db.log_action(user_id, "credit_interest", f"+${interest:.2f} пени")
            count += 1

        return count

    @staticmethod
    def get_credit_status(db, user_id: int) -> Dict:
        """Статус кредитов игрока"""
        active = db.get_active_credit(user_id)
        if not active:
            return {
                "has_credit": False,
                "message": (
                    f"💳 <b>Кредиты</b>\n\n"
                    f"У вас нет активных кредитов.\n\n"
                    f"<b>Доступные кредиты:</b>\n"
                    f"💵 Малый: +$200, вернуть $260 (12ч)\n"
                    f"💰 Средний: +$500, вернуть $700 (24ч)\n"
                    f"🏦 Большой: +$1000, вернуть $1500 (48ч)\n\n"
                    f"⚠️ Просрочка: +2% в час"
                )
            }

        remaining = active["repay_amount"] - active["paid_amount"]
        due = datetime.fromisoformat(active["due_time"])
        is_overdue = datetime.now() > due
        time_info = "❗ ПРОСРОЧЕН" if is_overdue else due.strftime("%d.%m %H:%M")

        return {
            "has_credit": True,
            "remaining": remaining,
            "is_overdue": is_overdue,
            "message": (
                f"💳 <b>Ваш кредит</b>\n\n"
                f"💸 Долг: <b>${remaining:.2f}</b>\n"
                f"⏰ Дедлайн: {time_info}\n"
                + (f"⚠️ <b>Идут пени +2% в час!</b>\n" if is_overdue else "")
                + f"\nИспользуйте /погасить для оплаты"
            )
        }

    @staticmethod
    def handle_bankruptcy(db, user_id: int) -> Dict:
        """
        Банкротство — частичное списание долга, продажа бизнесов.
        Игрок не удаляется.
        """
        active = db.get_active_credit(user_id)
        balance = db.get_balance(user_id)
        businesses = db.get_user_businesses(user_id)

        sold_value = 0.0
        sold_businesses = []

        # Продаём бизнесы за 50% цены
        for biz in businesses:
            biz_type = biz["business_type"]
            if biz_type in config.BUSINESSES:
                sell_price = config.BUSINESSES[biz_type]["base_cost"] * 0.5
                sold_value += sell_price
                sold_businesses.append(config.BUSINESSES[biz_type]["name"])
                db.remove_business(user_id, biz["id"])

        if sold_value > 0:
            db.update_balance(user_id, sold_value)

        forgiven = 0.0
        if active:
            debt = active["repay_amount"] - active["paid_amount"]
            forgiven = debt * config.BANKRUPTCY_DEBT_FORGIVE
            db.reduce_credit_debt(active["id"], forgiven)

        db.log_action(user_id, "bankruptcy", f"Банкротство: продано на ${sold_value}, списано ${forgiven}")

        lines = ["🏳️ <b>Банкротство</b>\n"]
        if sold_businesses:
            lines.append(f"🏭 Продано бизнесов: {', '.join(sold_businesses)}")
            lines.append(f"💰 Выручка: ${sold_value:.2f}")
        if forgiven > 0:
            lines.append(f"✂️ Списано долга: ${forgiven:.2f}")
        lines.append(f"\n💡 Начните с малого — купите лимонадную!")

        return {"success": True, "message": "\n".join(lines)}
