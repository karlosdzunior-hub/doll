"""
Сервис энергии - управление энергией игроков
"""

import random
from datetime import datetime, timedelta
from db import db
from config import config


class EnergyService:
    """
    Система энергии:
    - Энергия тратится бизнесами каждый час
    - Электростанции генерируют энергию
    - Базовая регенерация +1 каждые 10 минут
    - При 0 энергии бизнесы останавливаются
    """

    @staticmethod
    def process_energy_tick() -> dict:
        """
        Обработка тика энергии (каждые 5 минут)
        Возвращает статистику
        """
        stats = {
            "users_processed": 0,
            "out_of_energy": 0,
            "total_generated": 0,
            "total_consumed": 0,
        }

        users = db.get_all_users_energy()

        for user_data in users:
            user_id = user_data["user_id"]
            current_energy = user_data["energy"]
            max_energy = user_data["max_energy"]

            stats["users_processed"] += 1

            # Базовая регенерация: +1 каждые 10 минут (0.5 за тик 5 мин)
            base_regen = config.BASE_REGEN_RATE / 2

            # Генерация от электростанций
            energy_gen = db.get_total_energy_gen(user_id) / 12  # за 5 минут

            # Потребление бизнесов — только если энергии достаточно для работы
            if current_energy >= config.MIN_ENERGY_TO_WORK:
                energy_cost = db.get_total_energy_cost(user_id) / 12  # за 5 минут
            else:
                energy_cost = 0  # бизнесы не работают — энергия не тратится

            # Итого изменения
            net_change = energy_gen + base_regen - energy_cost

            # Обновляем энергию
            new_energy = max(0, min(max_energy, current_energy + net_change))
            db.set_energy(user_id, new_energy)

            # Статистика
            stats["total_generated"] += energy_gen + base_regen
            stats["total_consumed"] += energy_cost

            if new_energy <= 0:
                stats["out_of_energy"] += 1

        return stats

    @staticmethod
    def get_user_energy_status(user_id: int) -> dict:
        """Получить статус энергии пользователя"""
        current, max_e = db.get_energy(user_id)
        consumption = db.get_total_energy_cost(user_id)
        generation = db.get_total_energy_gen(user_id)
        net = generation + config.BASE_REGEN_RATE - consumption

        return {
            "current": current,
            "max": max_e,
            "percentage": (current / max_e) * 100 if max_e > 0 else 0,
            "consumption_per_hour": consumption,
            "generation_per_hour": generation + config.BASE_REGEN_RATE,
            "net_per_hour": net,
            "is_depleted": current < config.MIN_ENERGY_TO_WORK,
        }

    @staticmethod
    def add_energy(user_id: int, amount: int) -> bool:
        """Добавить энергию пользователю"""
        current, max_e = db.get_energy(user_id)
        new_energy = min(max_e, current + amount)
        return db.set_energy(user_id, new_energy)

    @staticmethod
    def can_businesses_work(user_id: int) -> bool:
        """Проверяет могут ли работать бизнесы"""
        current, _ = db.get_energy(user_id)
        return current >= config.MIN_ENERGY_TO_WORK

    @staticmethod
    def get_no_energy_message(user_id: int) -> str:
        """Сообщение когда энергия закончилась"""
        current, max_e = db.get_energy(user_id)

        return f"""⚠️ <b>Энергия закончилась!</b>

🔋 Энергия: {current:.0f}/{max_e}
⛔ Все бизнесы остановлены!

💡 <i>Энергия медленно восстанавливается (+1 каждые 10 минут)</i>
💡 <i>Минимум {config.MIN_ENERGY_TO_WORK} энергии для запуска бизнесов</i>"""

    @staticmethod
    def get_energy_bar(current: float, max_e: int, length: int = 10) -> str:
        """Генерация текстовой полоски энергии"""
        filled = int((current / max_e) * length)
        empty = length - filled

        if current > 60:
            color = "🟢"
        elif current > 30:
            color = "🟡"
        elif current >= config.MIN_ENERGY_TO_WORK:
            color = "🟠"
        else:
            color = "🔴"

        return f"{color}[{'█' * filled}{'░' * empty}]"
