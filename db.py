"""
Модуль работы с базой данных SQLite
Содержит все операции CRUD для пользователей, бизнесов, событий, ресурсов и рефералов
"""

import sqlite3
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from config import config


class Database:
    """Класс для работы с SQLite базой данных"""

    def __init__(self, db_name: str = "game.db"):
        self.db_name = db_name
        self.init_db()

    def get_connection(self):
        """Получить соединение с БД"""
        conn = sqlite3.connect(self.db_name)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self):
        """Инициализация таблиц базы данных"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Таблица пользователей
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    balance REAL DEFAULT 1.0,
                    vip_status INTEGER DEFAULT 0,
                    vip_expire DATETIME,
                    referral_id INTEGER,
                    last_event_date DATE,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Таблица бизнесов
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS businesses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    business_type TEXT,
                    name TEXT,
                    level INTEGER DEFAULT 1,
                    base_income REAL,
                    last_collect_time DATETIME,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            """)

            # Таблица событий
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS events_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    event_type TEXT,
                    effect_value REAL,
                    event_date DATE,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            """)

            # Таблица ресурсов (щиты, билеты)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS resources (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    resource_type TEXT,
                    quantity INTEGER DEFAULT 0,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            """)

            # Таблица рефералов
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS referrals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    referred_user_id INTEGER,
                    bonus_given REAL DEFAULT 0,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id),
                    FOREIGN KEY (referred_user_id) REFERENCES users(user_id)
                )
            """)

            conn.commit()

    # ============== ОПЕРАЦИИ С ПОЛЬЗОВАТЕЛЯМИ ==============

    def get_user(self, user_id: int) -> Optional[sqlite3.Row]:
        """Получить пользователя по ID"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            return cursor.fetchone()

    def create_user(
        self, user_id: int, username: str, referral_id: Optional[int] = None
    ) -> bool:
        """Создать нового пользователя"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                # Проверяем, существует ли пользователь
                cursor.execute(
                    "SELECT user_id FROM users WHERE user_id = ?", (user_id,)
                )
                if cursor.fetchone():
                    return False

                # Создаём пользователя
                cursor.execute(
                    """
                    INSERT INTO users (user_id, username, balance, referral_id)
                    VALUES (?, ?, ?, ?)
                """,
                    (user_id, username, config.STARTING_BALANCE, referral_id),
                )

                # Если есть реферал - начисляем бонус обоим
                if referral_id:
                    self._give_referral_bonus(referral_id, user_id)

                conn.commit()
                return True
        except Exception as e:
            print(f"Error creating user: {e}")
            return False

    def _give_referral_bonus(self, referrer_id: int, new_user_id: int):
        """Начислить бонус рефереру и новому пользователю"""
        cursor = conn.cursor()
        bonus = config.REFERRAL_BONUS

        # Бонус рефереру
        cursor.execute(
            "UPDATE users SET balance = balance + ? WHERE user_id = ?",
            (bonus, referrer_id),
        )

        # Запись в таблицу рефералов
        cursor.execute(
            """
            INSERT INTO referrals (user_id, referred_user_id, bonus_given)
            VALUES (?, ?, ?)
        """,
            (referrer_id, new_user_id, bonus),
        )

    def update_balance(self, user_id: int, amount: float) -> bool:
        """Изменить баланс пользователя"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE users SET balance = balance + ? WHERE user_id = ?",
                    (amount, user_id),
                )
                conn.commit()
                return True
        except:
            return False

    def set_balance(self, user_id: int, amount: float) -> bool:
        """Установить баланс пользователя"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE users SET balance = ? WHERE user_id = ?", (amount, user_id)
                )
                conn.commit()
                return True
        except:
            return False

    def get_balance(self, user_id: int) -> float:
        """Получить баланс пользователя"""
        user = self.get_user(user_id)
        return float(user["balance"]) if user else 0.0

    def set_vip(self, user_id: int, days: int = 7) -> bool:
        """Активировать VIP статус"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                expire_date = datetime.now() + timedelta(days=days)
                cursor.execute(
                    """
                    UPDATE users 
                    SET vip_status = 1, vip_expire = ?
                    WHERE user_id = ?
                """,
                    (expire_date, user_id),
                )
                conn.commit()
                return True
        except:
            return False

    def check_vip(self, user_id: int) -> bool:
        """Проверить активен ли VIP"""
        user = self.get_user(user_id)
        if not user or not user["vip_status"]:
            return False
        if user["vip_expire"]:
            expire = datetime.fromisoformat(user["vip_expire"])
            return datetime.now() < expire
        return False

    def get_referral_count(self, user_id: int) -> int:
        """Получить количество рефералов"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT COUNT(*) FROM referrals WHERE user_id = ?", (user_id,)
            )
            return cursor.fetchone()[0]

    def get_referrals(self, user_id: int) -> List[sqlite3.Row]:
        """Получить список рефералов пользователя"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT r.*, u.username 
                FROM referrals r
                JOIN users u ON r.referred_user_id = u.user_id
                WHERE r.user_id = ?
            """,
                (user_id,),
            )
            return cursor.fetchall()

    # ============== ОПЕРАЦИИ С БИЗНЕСАМИ ==============

    def get_user_businesses(self, user_id: int) -> List[sqlite3.Row]:
        """Получить все бизнесы пользователя"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM businesses WHERE user_id = ?", (user_id,))
            return cursor.fetchall()

    def get_business(self, business_id: int) -> Optional[sqlite3.Row]:
        """Получить бизнес по ID"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM businesses WHERE id = ?", (business_id,))
            return cursor.fetchone()

    def create_business(self, user_id: int, business_type: str) -> bool:
        """Создать новый бизнес"""
        try:
            if business_type not in config.BUSINESS_TYPES:
                return False

            biz_config = config.BUSINESS_TYPES[business_type]
            cost = biz_config["base_cost"]

            # Проверяем баланс
            if self.get_balance(user_id) < cost:
                return False

            with self.get_connection() as conn:
                cursor = conn.cursor()

                # Списываем стоимость
                cursor.execute(
                    "UPDATE users SET balance = balance - ? WHERE user_id = ?",
                    (cost, user_id),
                )

                # Создаём бизнес
                cursor.execute(
                    """
                    INSERT INTO businesses (user_id, business_type, name, level, base_income, last_collect_time)
                    VALUES (?, ?, ?, 1, ?, ?)
                """,
                    (
                        user_id,
                        business_type,
                        biz_config["name"],
                        biz_config["base_income"],
                        datetime.now(),
                    ),
                )

                conn.commit()
                return True
        except Exception as e:
            print(f"Error creating business: {e}")
            return False

    def upgrade_business(self, business_id: int) -> tuple[bool, float]:
        """Улучшить бизнес. Возвращает (успех, новая стоимость)"""
        business = self.get_business(business_id)
        if not business:
            return False, 0

        biz_type = business["business_type"]
        biz_config = config.BUSINESS_TYPES[biz_type]
        new_level = business["level"] + 1

        # Стоимость апгрейда
        upgrade_cost = business["base_income"] * (
            biz_config["upgrade_cost_multiplier"] ** (new_level - 1)
        )

        # Проверяем баланс
        if self.get_balance(business["user_id"]) < upgrade_cost:
            return False, upgrade_cost

        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                # Списываем стоимость
                cursor.execute(
                    "UPDATE users SET balance = balance - ? WHERE user_id = ?",
                    (upgrade_cost, business["user_id"]),
                )

                # Повышаем уровень
                cursor.execute(
                    "UPDATE businesses SET level = ? WHERE id = ?",
                    (new_level, business_id),
                )

                conn.commit()
                return True, upgrade_cost
        except:
            return False, upgrade_cost

    def instant_upgrade_business(self, business_id: int) -> bool:
        """Мгновенный апгрейд бизнеса за Stars"""
        return self.upgrade_business(business_id)[0]

    def get_business_income(self, business_id: int) -> float:
        """Рассчитать доход бизнеса: уровень * базовый доход"""
        business = self.get_business(business_id)
        if not business:
            return 0.0
        return float(business["level"] * business["base_income"])

    def get_total_income(self, user_id: int) -> float:
        """Получить общий доход пользователя со всех бизнесов"""
        businesses = self.get_user_businesses(user_id)
        return sum(self.get_business_income(b.id) for b in businesses)

    # ============== ОПЕРАЦИИ С СОБЫТИЯМИ ==============

    def get_last_event_date(self, user_id: int) -> Optional[str]:
        """Получить дату последнего события"""
        user = self.get_user(user_id)
        return user["last_event_date"] if user else None

    def set_last_event_date(self, user_id: int, date: str):
        """Установить дату последнего события"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE users SET last_event_date = ? WHERE user_id = ?",
                (date, user_id),
            )
            conn.commit()

    def log_event(self, user_id: int, event_type: str, effect_value: float):
        """Записать событие в лог"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO events_log (user_id, event_type, effect_value, event_date)
                VALUES (?, ?, ?, ?)
            """,
                (user_id, event_type, effect_value, datetime.now().date().isoformat()),
            )
            conn.commit()

    def get_user_events(self, user_id: int, limit: int = 10) -> List[sqlite3.Row]:
        """Получить историю событий пользователя"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * FROM events_log 
                WHERE user_id = ? 
                ORDER BY created_at DESC 
                LIMIT ?
            """,
                (user_id, limit),
            )
            return cursor.fetchall()

    # ============== ОПЕРАЦИИ С РЕСУРСАМИ ==============

    def get_resource(self, user_id: int, resource_type: str) -> int:
        """Получить количество ресурса"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT quantity FROM resources 
                WHERE user_id = ? AND resource_type = ?
            """,
                (user_id, resource_type),
            )
            result = cursor.fetchone()
            return result[0] if result else 0

    def add_resource(self, user_id: int, resource_type: str, quantity: int = 1):
        """Добавить ресурс пользователю"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO resources (user_id, resource_type, quantity)
                VALUES (?, ?, ?)
                ON CONFLICT(user_id, resource_type) 
                DO UPDATE SET quantity = quantity + ?
            """,
                (user_id, resource_type, quantity, quantity),
            )
            conn.commit()

    def use_resource(self, user_id: int, resource_type: str) -> bool:
        """Использовать ресурс (уменьшить на 1)"""
        if self.get_resource(user_id, resource_type) < 1:
            return False

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE resources 
                SET quantity = quantity - 1 
                WHERE user_id = ? AND resource_type = ? AND quantity > 0
            """,
                (user_id, resource_type),
            )
            conn.commit()
            return True

    def get_all_resources(self, user_id: int) -> Dict[str, int]:
        """Получить все ресурсы пользователя"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT resource_type, quantity FROM resources WHERE user_id = ?",
                (user_id,),
            )
            return {row["resource_type"]: row["quantity"] for row in cursor.fetchall()}

    # ============== ЛИДЕРБОРД ==============

    def get_leaderboard(self, limit: int = 10) -> List[sqlite3.Row]:
        """Получить топ игроков по балансу"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT user_id, username, balance 
                FROM users 
                ORDER BY balance DESC 
                LIMIT ?
            """,
                (limit,),
            )
            return cursor.fetchall()


# Глобальный экземпляр БД
db = Database()
