"""
Сервис чатов - управление уровнями, XP и бонусами чатов
"""

from db import db
from config import config
from services.energy import EnergyService


class ChatService:
    """
    Система уровней чатов:
    - XP за активность
    - Уровни с бонусами
    - Награды за повышение уровня
    """

    @staticmethod
    def add_xp_for_action(chat_id: int, action: str):
        """Добавить XP за определённое действие"""
        xp_map = {
            "command": config.XP_PER_COMMAND,
            "transfer": config.XP_PER_TRANSFER,
            "lottery": config.XP_PER_LOTTERY,
            "new_user": config.XP_PER_NEW_USER,
        }

        xp = xp_map.get(action, 1)
        success, leveled_up, new_level = db.add_chat_xp(chat_id, xp)

        return success, leveled_up, new_level

    @staticmethod
    def process_level_up(chat_id: int, new_level: int, bot) -> str:
        """Обработка повышения уровня чата"""
        chat = db.get_chat(chat_id)
        if not chat:
            return ""

        # Получаем всех пользователей чата
        # TODO: Реализовать получение списка пользователей через API

        # Отправляем сообщение о повышении
        message = f"""🎉 <b>Чат достиг уровня {new_level}!</b>

🏆 Новые бонусы активированы!
⚡ +{config.CHAT_LEVEL_UP_ENERGY_BONUS} энергии всем участникам!"""

        return message

    @staticmethod
    def get_chat_stats(chat_id: int) -> dict:
        """Получить статистику чата"""
        chat = db.get_chat(chat_id)
        if not chat:
            return None

        xp_needed = db.get_xp_needed_for_level(chat["level"])
        bonuses = db.get_chat_bonus(chat_id)

        return {
            "chat_id": chat_id,
            "title": chat["title"],
            "level": chat["level"],
            "xp": chat["xp"],
            "xp_needed": xp_needed,
            "progress": (chat["xp"] / xp_needed * 100) if xp_needed > 0 else 0,
            "bonuses": bonuses,
        }

    @staticmethod
    def apply_chat_bonuses(user_id: int, chat_id: int) -> dict:
        """Применить бонусы чата к игроку"""
        bonuses = db.get_chat_bonus(chat_id)

        return {
            "income_multiplier": 1 + bonuses.get("income_bonus", 0),
            "energy_discount": bonuses.get("energy_discount", 0),
            "jackpot_chance_bonus": bonuses.get("jackpot_chance_bonus", 0),
            "free_tickets": bonuses.get("free_tickets", 0),
        }

    @staticmethod
    def get_all_chats_sorted() -> list:
        """Получить все чаты отсортированные по уровню"""
        return db.get_top_chats(100)
