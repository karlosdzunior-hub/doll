"""
Сервис уведомлений — давление на игрока, напоминания о долге
"""

from datetime import datetime
from typing import Optional


class NotificationService:

    # --- Шаблоны сообщений ---

    DEBT_WARNING = (
        "⚠️ <b>Внимание!</b>\n\n"
        "Ваш долг <b>${debt:.2f}</b> просрочен!\n"
        "Каждый час начисляется +2%.\n\n"
        "🆘 Срочно погасите: /погасить\n"
        "💳 Или задонатьте: /магазин\n"
        "🎰 Попробуйте джекпот: /джекпот"
    )

    DEBT_CRITICAL = (
        "🚨 <b>КРИТИЧЕСКИЙ ДОЛГ!</b>\n\n"
        "Вы должны <b>${debt:.2f}</b>!\n"
        "Долг продолжает расти...\n\n"
        "🏳️ Объявить банкротство: /банкротство\n"
        "💳 Купить энергию: /магазин\n"
        "🎰 Джекпот ${bank:.2f}: /джекпот"
    )

    NEGATIVE_BALANCE = (
        "📉 <b>Вы в минусе!</b>\n\n"
        "Баланс: <b>${balance:.2f}</b>\n\n"
        "💡 Варианты:\n"
        "• Продайте бизнес: /мои_бизнесы\n"
        "• Возьмите кредит: /кредит\n"
        "• Сыграйте в джекпот: /джекпот"
    )

    JACKPOT_BANK_GROWING = (
        "🎰 <b>Банк джекпота растёт!</b>\n\n"
        "💰 Уже <b>${bank:.2f}</b>!\n"
        "⏰ Розыгрыш через {time_left}\n\n"
        "🎫 Купить билет (${ticket_cost}): /джекпот"
    )

    PASSIVE_INCOME = (
        "💰 <b>Пассивный доход!</b>\n\n"
        "Ваши бизнесы работали пока вас не было.\n"
        "📈 Проверьте баланс: /баланс"
    )

    ENERGY_LOW = (
        "⚡ <b>Низкая энергия!</b>\n\n"
        "Энергия: {energy}/100\n"
        "Бизнесы не работают при < 10 энергии!\n\n"
        "🔋 Купить энергию: /магазин"
    )

    @staticmethod
    def format_debt_warning(debt: float) -> str:
        return NotificationService.DEBT_WARNING.format(debt=debt)

    @staticmethod
    def format_debt_critical(debt: float, bank: float) -> str:
        return NotificationService.DEBT_CRITICAL.format(debt=debt, bank=bank)

    @staticmethod
    def format_negative_balance(balance: float) -> str:
        return NotificationService.NEGATIVE_BALANCE.format(balance=balance)

    @staticmethod
    def format_jackpot_growing(bank: float, time_left: str, ticket_cost: float) -> str:
        return NotificationService.JACKPOT_BANK_GROWING.format(
            bank=bank, time_left=time_left, ticket_cost=ticket_cost
        )

    @staticmethod
    def format_energy_low(energy: int) -> str:
        return NotificationService.ENERGY_LOW.format(energy=energy)

    @staticmethod
    def should_notify_debt(last_notified: Optional[datetime], hours: int = 3) -> bool:
        """Проверка — пора ли слать уведомление о долге"""
        if not last_notified:
            return True
        delta = datetime.now() - last_notified
        return delta.total_seconds() >= hours * 3600

    @staticmethod
    def build_onboarding_message(username: str, balance: float, energy: int, tickets: int) -> str:
        return (
            f"👋 <b>Привет, {username}!</b>\n\n"
            f"🎮 <b>Микрокапитализм: Жизнь на 1 доллар</b>\n\n"
            f"📦 Стартовый пакет:\n"
            f"💰 Баланс: <b>${balance:.0f}</b>\n"
            f"⚡ Энергия: <b>{energy}/100</b>\n"
            f"🎫 Билеты джекпота: <b>{tickets}</b>\n\n"
            f"🎯 Цель: зарабатывай, вкладывай, побеждай!\n\n"
            f"🚀 С чего начать:\n"
            f"• Купи первый бизнес → /магазин\n"
            f"• Сыграй в джекпот → /джекпот\n"
            f"• Посмотри баланс → /баланс"
        )
