"""
Сервис джекпота — розыгрыш каждые 6 часов
50% → банк, 30% → сжигание, 20% → система
"""

import random
from datetime import datetime, timedelta
from typing import Optional, Dict

from config import config


class JackpotService:

    @staticmethod
    def buy_ticket(db, user_id: int, count: int = 1) -> Dict:
        """Купить билет(ы) за $10 каждый"""
        total_cost = config.JACKPOT_TICKET_COST * count
        balance = db.get_balance(user_id)

        if balance < total_cost:
            return {"success": False, "error": f"Недостаточно средств. Нужно ${total_cost:.0f}, у вас ${balance:.2f}"}

        # Списываем деньги
        db.update_balance(user_id, -total_cost)

        # Распределяем: 50% в банк джекпота
        bank_amount = total_cost * config.JACKPOT_BANK_SHARE
        db.add_to_jackpot_bank(bank_amount)

        # Добавляем билеты игроку
        db.add_jackpot_tickets(user_id, count)

        # Логируем покупку
        db.log_action(user_id, "jackpot_buy", f"Куплено {count} билетов за ${total_cost}")

        bank = db.get_jackpot_bank()
        return {
            "success": True,
            "count": count,
            "cost": total_cost,
            "bank": bank,
            "message": (
                f"🎫 Куплено <b>{count}</b> билет(ов) за <b>${total_cost:.0f}</b>\n"
                f"💰 Банк джекпота: <b>${bank:.2f}</b>"
            )
        }

    @staticmethod
    def get_next_draw_time(db) -> Optional[datetime]:
        """Получить время следующего розыгрыша"""
        last = db.get_last_jackpot_draw()
        if not last:
            return datetime.now()
        return last + timedelta(hours=config.JACKPOT_INTERVAL_HOURS)

    @staticmethod
    def time_until_draw(db) -> str:
        """Сколько времени до следующего розыгрыша"""
        next_draw = JackpotService.get_next_draw_time(db)
        delta = next_draw - datetime.now()
        if delta.total_seconds() <= 0:
            return "⚡ Скоро!"
        h = int(delta.total_seconds() // 3600)
        m = int((delta.total_seconds() % 3600) // 60)
        s = int(delta.total_seconds() % 60)
        if h > 0:
            return f"{h}ч {m}м"
        elif m > 0:
            return f"{m}м {s}с"
        return f"{s}с"

    @staticmethod
    def run_draw(db) -> Optional[Dict]:
        """
        Провести розыгрыш.
        Возвращает словарь с победителем или None если участников нет.
        """
        participants = db.get_jackpot_participants()
        bank = db.get_jackpot_bank()

        if not participants or bank <= 0:
            db.set_jackpot_draw_time()
            return None

        # Выбираем победителя (взвешено — больше билетов = больше шансов)
        ticket_pool = []
        for p in participants:
            ticket_pool.extend([p["user_id"]] * p["tickets"])

        winner_id = random.choice(ticket_pool)
        winner_info = db.get_user(winner_id)

        # Начисляем выигрыш
        db.update_balance(winner_id, bank)

        # Обнуляем банк и билеты
        db.reset_jackpot_pool()
        db.set_jackpot_draw_time()

        db.log_action(winner_id, "jackpot_win", f"Выиграл джекпот ${bank:.2f}")

        return {
            "winner_id": winner_id,
            "winner_name": winner_info.get("username", f"User{winner_id}") if winner_info else f"User{winner_id}",
            "prize": bank,
            "participants": len(set(ticket_pool)),
            "total_tickets": len(ticket_pool),
            "message": (
                f"🎰 <b>ДЖЕКПОТ РОЗЫГРЫШ!</b>\n\n"
                f"🏆 Победитель: @{winner_info.get('username', 'игрок') if winner_info else 'игрок'}\n"
                f"💰 Выигрыш: <b>${bank:.2f}</b>\n"
                f"🎫 Участвовало: {len(set(ticket_pool))} игроков, {len(ticket_pool)} билетов"
            )
        }

    @staticmethod
    def first_ticket_spin(db, user_id: int) -> Dict:
        """Гарантированный выигрыш x1.5 для онбординга"""
        stake = config.JACKPOT_TICKET_COST
        prize = stake * config.JACKPOT_FIRST_WIN_MULTIPLIER
        db.update_balance(user_id, prize - stake)
        db.use_jackpot_ticket(user_id)
        db.log_action(user_id, "jackpot_first_win", f"Первый выигрыш x1.5 = ${prize}")
        return {
            "success": True,
            "multiplier": config.JACKPOT_FIRST_WIN_MULTIPLIER,
            "prize": prize,
            "message": (
                f"🎰 <b>ПОЧТИ... И ВЫИГРЫШ!</b>\n\n"
                f"🎉 Поздравляем с первым розыгрышем!\n"
                f"💰 Вы выиграли <b>x{config.JACKPOT_FIRST_WIN_MULTIPLIER}</b> = <b>${prize:.2f}</b>!\n\n"
                f"🏆 Банк растёт каждый час. Покупай больше билетов!"
            )
        }

    @staticmethod
    def get_status(db) -> Dict:
        """Статус джекпота"""
        bank = db.get_jackpot_bank()
        participants = db.get_jackpot_participants()
        total_tickets = sum(p["tickets"] for p in participants)
        time_left = JackpotService.time_until_draw(db)

        return {
            "bank": bank,
            "participants": len(participants),
            "total_tickets": total_tickets,
            "time_left": time_left,
            "message": (
                f"🎰 <b>ДЖЕКПОТ</b>\n\n"
                f"💰 Банк: <b>${bank:.2f}</b>\n"
                f"🎫 Билет: ${config.JACKPOT_TICKET_COST:.0f}\n"
                f"👥 Участников: {len(participants)}\n"
                f"🎟️ Всего билетов: {total_tickets}\n"
                f"⏰ До розыгрыша: {time_left}\n\n"
                f"<i>50% от каждого билета → в банк</i>"
            )
        }
