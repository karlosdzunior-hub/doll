"""
Database module - работа с базой данных (Production с энергией)
"""

import sqlite3
import random
from datetime import datetime, timedelta
from typing import Optional, List, Dict
from contextlib import contextmanager
from config import config


class Database:
    def __init__(self, db_path: str = "game.db"):
        self.db_path = db_path
        self.init_db()

    @contextmanager
    def get_connection(self):
        conn = sqlite3.connect(self.db_path, timeout=30)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def init_db(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Пользователи с энергией
            cursor.execute("""CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                balance REAL DEFAULT 1.0,
                energy REAL DEFAULT 100.0,
                max_energy INTEGER DEFAULT 100,
                vip_status INTEGER DEFAULT 0,
                vip_expire DATETIME,
                boost_expire DATETIME,
                referral_id INTEGER,
                last_energy_update DATETIME DEFAULT CURRENT_TIMESTAMP,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )""")

            # Бизнесы
            cursor.execute("""CREATE TABLE IF NOT EXISTS businesses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                business_type TEXT,
                level INTEGER DEFAULT 1,
                active INTEGER DEFAULT 1,
                last_produce DATETIME DEFAULT CURRENT_TIMESTAMP,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )""")

            # Ресурсы игроков
            cursor.execute("""CREATE TABLE IF NOT EXISTS user_resources (
                user_id INTEGER,
                resource_type TEXT,
                quantity REAL DEFAULT 0,
                PRIMARY KEY (user_id, resource_type)
            )""")

            # Цены на рынке
            cursor.execute("""CREATE TABLE IF NOT EXISTS market_prices (
                resource_type TEXT PRIMARY KEY,
                current_price REAL,
                base_price REAL,
                demand REAL DEFAULT 0,
                supply REAL DEFAULT 0,
                last_update DATETIME DEFAULT CURRENT_TIMESTAMP
            )""")

            # Ордера на рынке
            cursor.execute("""CREATE TABLE IF NOT EXISTS market_orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                resource_type TEXT,
                order_type TEXT,
                quantity REAL,
                price REAL,
                status TEXT DEFAULT 'active',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )""")

            # Транзакции (переводы)
            cursor.execute("""CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                from_user INTEGER,
                to_user INTEGER,
                amount REAL,
                fee REAL,
                chat_id INTEGER,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )""")

            # Рефералы
            cursor.execute("""CREATE TABLE IF NOT EXISTS referrals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                referred_user_id INTEGER,
                bonus_given REAL DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )""")

            # Предметы
            cursor.execute("""CREATE TABLE IF NOT EXISTS items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                item_type TEXT,
                quantity INTEGER DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )""")

            # Глобальные события
            cursor.execute("""CREATE TABLE IF NOT EXISTS global_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT,
                multiplier REAL,
                affected_resource TEXT,
                message TEXT,
                starts_at DATETIME,
                ends_at DATETIME,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )""")

            # Лог событий игроков
            cursor.execute("""CREATE TABLE IF NOT EXISTS user_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                event_type TEXT,
                message TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )""")

            # Таблица чатов с уровнями
            cursor.execute("""CREATE TABLE IF NOT EXISTS chats (
                chat_id INTEGER PRIMARY KEY,
                chat_type TEXT,
                title TEXT,
                added_by_user_id INTEGER,
                level INTEGER DEFAULT 1,
                xp INTEGER DEFAULT 0,
                bonus_claimed INTEGER DEFAULT 0,
                vip_status INTEGER DEFAULT 0,
                vip_expire DATETIME,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )""")

            # Участники чата
            cursor.execute("""CREATE TABLE IF NOT EXISTS chat_users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER,
                user_id INTEGER,
                joined_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                daily_transfer_used REAL DEFAULT 0,
                last_transfer_reset DATE DEFAULT (date('now')),
                UNIQUE(chat_id, user_id)
            )""")

            # Лотерея
            cursor.execute("""CREATE TABLE IF NOT EXISTS lottery (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                chat_id INTEGER,
                ticket_type TEXT DEFAULT 'regular',
                stake REAL DEFAULT 10,
                multiplier REAL DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )""")

            # Лог всех действий
            cursor.execute("""CREATE TABLE IF NOT EXISTS action_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                action_type TEXT,
                details TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )""")

            # Банк джекпота
            cursor.execute("""CREATE TABLE IF NOT EXISTS jackpot_bank (
                id INTEGER PRIMARY KEY DEFAULT 1,
                amount REAL DEFAULT 0.0,
                last_draw DATETIME,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )""")
            cursor.execute("INSERT OR IGNORE INTO jackpot_bank (id, amount) VALUES (1, 0.0)")

            # Билеты джекпота у игроков
            cursor.execute("""CREATE TABLE IF NOT EXISTS jackpot_tickets (
                user_id INTEGER PRIMARY KEY,
                tickets INTEGER DEFAULT 0,
                first_used INTEGER DEFAULT 0,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )""")

            # Кредиты / займы
            cursor.execute("""CREATE TABLE IF NOT EXISTS credits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                credit_type TEXT,
                amount REAL,
                repay_amount REAL,
                paid_amount REAL DEFAULT 0.0,
                due_time DATETIME,
                status TEXT DEFAULT 'active',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )""")

            # Таблица платежей (Telegram Stars)
            cursor.execute("""CREATE TABLE IF NOT EXISTS payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                chat_id INTEGER,
                item_type TEXT,
                amount INTEGER,
                stars_amount INTEGER,
                status TEXT DEFAULT 'pending',
                provider_token TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )""")

            # Индексы для чатов
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_chats_level ON chats(level DESC)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_payments_user ON payments(user_id)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_payments_chat ON payments(chat_id)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_businesses_user ON businesses(user_id)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_transactions_from ON transactions(from_user)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_user_events ON user_events(user_id)"
            )

            # Инициализация рынка
            for resource_type, data in config.RESOURCES.items():
                cursor.execute(
                    """INSERT OR IGNORE INTO market_prices 
                    (resource_type, current_price, base_price, demand, supply) 
                    VALUES (?, ?, ?, 0, 0)""",
                    (resource_type, data["base_price"], data["base_price"]),
                )

            conn.commit()

    # ==================== ПОЛЬЗОВАТЕЛИ ====================

    def get_user(self, user_id: int) -> Optional[sqlite3.Row]:
        with self.get_connection() as conn:
            return (
                conn.cursor()
                .execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
                .fetchone()
            )

    def create_user(
        self, user_id: int, username: str, referral_id: Optional[int] = None
    ) -> bool:
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT user_id FROM users WHERE user_id = ?", (user_id,)
                )
                if cursor.fetchone():
                    return False

                cursor.execute(
                    """INSERT INTO users (user_id, username, balance, energy, referral_id)
                    VALUES (?, ?, ?, ?, ?)""",
                    (
                        user_id,
                        username,
                        config.STARTING_BALANCE,
                        float(config.STARTING_ENERGY),
                        referral_id,
                    ),
                )

                # Ресурсы
                for resource_type in config.RESOURCES.keys():
                    cursor.execute(
                        """INSERT INTO user_resources (user_id, resource_type, quantity)
                        VALUES (?, ?, 0)""",
                        (user_id, resource_type),
                    )

                # Бонус рефереру
                if referral_id:
                    cursor.execute(
                        "UPDATE users SET balance = balance + ? WHERE user_id = ?",
                        (config.REFERRAL_BONUS, referral_id),
                    )
                    cursor.execute(
                        """INSERT INTO referrals (user_id, referred_user_id, bonus_given)
                        VALUES (?, ?, ?)""",
                        (referral_id, user_id, config.REFERRAL_BONUS),
                    )

                return True
        except Exception as e:
            print(f"Error creating user: {e}")
            return False

    def get_balance(self, user_id: int) -> float:
        user = self.get_user(user_id)
        return float(user["balance"]) if user else 0.0

    def update_balance(self, user_id: int, amount: float) -> bool:
        try:
            with self.get_connection() as conn:
                conn.cursor().execute(
                    "UPDATE users SET balance = balance + ? WHERE user_id = ?",
                    (amount, user_id),
                )
                return True
        except:
            return False

    def set_balance(self, user_id: int, amount: float) -> bool:
        try:
            with self.get_connection() as conn:
                conn.cursor().execute(
                    "UPDATE users SET balance = ? WHERE user_id = ?", (amount, user_id)
                )
                return True
        except:
            return False

    # ==================== ЭНЕРГИЯ ====================

    def get_energy(self, user_id: int) -> tuple:
        user = self.get_user(user_id)
        if not user:
            return 0, config.MAX_ENERGY
        return float(user["energy"]), int(user["max_energy"])

    def update_energy(self, user_id: int, delta: float) -> bool:
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE users SET energy = MAX(0, MIN(max_energy, energy + ?)) WHERE user_id = ?",
                    (delta, user_id),
                )
                cursor.execute(
                    "UPDATE users SET last_energy_update = CURRENT_TIMESTAMP WHERE user_id = ?",
                    (user_id,),
                )
                return True
        except:
            return False

    def set_energy(self, user_id: int, amount: float) -> bool:
        try:
            with self.get_connection() as conn:
                conn.cursor().execute(
                    "UPDATE users SET energy = ? WHERE user_id = ?",
                    (max(0, min(config.MAX_ENERGY, amount)), user_id),
                )
                return True
        except:
            return False

    def get_all_users_energy(self) -> List[Dict]:
        with self.get_connection() as conn:
            rows = (
                conn.cursor()
                .execute("""
                SELECT user_id, energy, max_energy, last_energy_update, vip_status, vip_expire
                FROM users
            """)
                .fetchall()
            )
            return [dict(row) for row in rows]

    def check_vip(self, user_id: int) -> bool:
        user = self.get_user(user_id)
        if not user or not user["vip_status"]:
            return False
        if user["vip_expire"]:
            return datetime.fromisoformat(user["vip_expire"]) > datetime.now()
        return False

    def set_vip(self, user_id: int, days: int = 7) -> bool:
        try:
            with self.get_connection() as conn:
                expire = datetime.now() + timedelta(days=days)
                conn.cursor().execute(
                    "UPDATE users SET vip_status = 1, vip_expire = ? WHERE user_id = ?",
                    (expire, user_id),
                )
                return True
        except:
            return False

    def check_boost(self, user_id: int) -> bool:
        user = self.get_user(user_id)
        if not user or not user["boost_expire"]:
            return False
        return datetime.fromisoformat(user["boost_expire"]) > datetime.now()

    def set_boost(self, user_id: int, hours: int = 1) -> bool:
        try:
            with self.get_connection() as conn:
                expire = datetime.now() + timedelta(hours=hours)
                conn.cursor().execute(
                    "UPDATE users SET boost_expire = ? WHERE user_id = ?",
                    (expire, user_id),
                )
                return True
        except:
            return False

    # ==================== БИЗНЕСЫ ====================

    def get_user_businesses(self, user_id: int) -> List[sqlite3.Row]:
        with self.get_connection() as conn:
            return (
                conn.cursor()
                .execute("SELECT * FROM businesses WHERE user_id = ?", (user_id,))
                .fetchall()
            )

    def get_business(self, business_id: int) -> Optional[sqlite3.Row]:
        with self.get_connection() as conn:
            return (
                conn.cursor()
                .execute("SELECT * FROM businesses WHERE id = ?", (business_id,))
                .fetchone()
            )

    def create_business(self, user_id: int, business_type: str) -> bool:
        if business_type not in config.BUSINESSES:
            return False
        biz = config.BUSINESSES[business_type]
        cost = biz["base_cost"]

        if self.get_balance(user_id) < cost:
            return False

        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE users SET balance = balance - ? WHERE user_id = ?",
                    (cost, user_id),
                )
                cursor.execute(
                    """INSERT INTO businesses (user_id, business_type, level)
                    VALUES (?, ?, 1)""",
                    (user_id, business_type),
                )
                return True
        except:
            return False

    def upgrade_business(self, business_id: int) -> tuple:
        business = self.get_business(business_id)
        if not business:
            return False, 0

        biz_type = business["business_type"]
        biz_config = config.BUSINESSES.get(biz_type, {})
        new_level = business["level"] + 1
        cost = biz_config.get("base_cost", 1) * (new_level**1.5)

        if self.get_balance(business["user_id"]) < cost:
            return False, cost

        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE users SET balance = balance - ? WHERE user_id = ?",
                    (cost, business["user_id"]),
                )
                cursor.execute(
                    "UPDATE businesses SET level = ? WHERE id = ?",
                    (new_level, business_id),
                )
                return True, cost
        except:
            return False, cost

    def get_total_energy_cost(self, user_id: int) -> float:
        """Общий расход энергии в час"""
        businesses = self.get_user_businesses(user_id)
        total = 0.0
        vip_discount = config.VIP_ENERGY_DISCOUNT if self.check_vip(user_id) else 0

        for biz in businesses:
            biz_type = biz["business_type"]
            if biz_type in config.BUSINESSES:
                cost = config.BUSINESSES[biz_type].get("energy_cost", 0)
                cost *= biz["level"]
                cost *= 1 - vip_discount
                total += cost

        return total

    def get_total_energy_gen(self, user_id: int) -> float:
        """Общая генерация энергии в час"""
        businesses = self.get_user_businesses(user_id)
        total = 0.0

        for biz in businesses:
            biz_type = biz["business_type"]
            if biz_type in config.BUSINESSES:
                gen = config.BUSINESSES[biz_type].get("energy_gen", 0)
                total += gen * biz["level"]

        return total

    def get_total_production(self, user_id: int) -> Dict[str, float]:
        """Производство ресурсов в час"""
        businesses = self.get_user_businesses(user_id)
        production = {}
        vip_bonus = 1 + (config.VIP_PRODUCTION_BONUS if self.check_vip(user_id) else 0)
        boost_bonus = 2 if self.check_boost(user_id) else 1

        for biz in businesses:
            biz_type = biz["business_type"]
            if biz_type in config.BUSINESSES:
                biz_config = config.BUSINESSES[biz_type]
                resource = biz_config["resource"]
                rate = (
                    biz_config["production_rate"]
                    * biz["level"]
                    * vip_bonus
                    * boost_bonus
                )
                production[resource] = production.get(resource, 0) + rate

        return production

    # ==================== РЕСУРСЫ ====================

    def get_user_resources(self, user_id: int) -> Dict[str, float]:
        with self.get_connection() as conn:
            rows = (
                conn.cursor()
                .execute(
                    "SELECT resource_type, quantity FROM user_resources WHERE user_id = ?",
                    (user_id,),
                )
                .fetchall()
            )
            return {row["resource_type"]: float(row["quantity"]) for row in rows}

    def update_user_resource(self, user_id: int, resource_type: str, quantity: float):
        with self.get_connection() as conn:
            conn.cursor().execute(
                """INSERT INTO user_resources (user_id, resource_type, quantity)
                VALUES (?, ?, ?) ON CONFLICT(user_id, resource_type)
                DO UPDATE SET quantity = MAX(0, MIN(?, quantity + ?))""",
                (user_id, resource_type, quantity, config.RESOURCE_MAX, quantity),
            )

    # ==================== РЫНОК ====================

    def get_market_prices(self) -> Dict[str, dict]:
        with self.get_connection() as conn:
            rows = conn.cursor().execute("SELECT * FROM market_prices").fetchall()
            return {row["resource_type"]: dict(row) for row in rows}

    def update_market_price(
        self, resource_type: str, demand_delta: float = 0, supply_delta: float = 0
    ):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM market_prices WHERE resource_type = ?", (resource_type,)
            )
            row = cursor.fetchone()
            if not row:
                return

            base = float(row["base_price"])
            demand = float(row["demand"]) + demand_delta
            supply = float(row["supply"]) + supply_delta

            # Формула цены
            price = base * (1 + (demand - supply) / (supply + 10))
            price = max(
                base * config.MIN_PRICE_MULTIPLIER,
                min(base * config.MAX_PRICE_MULTIPLIER, price),
            )

            cursor.execute(
                """UPDATE market_prices 
                SET current_price = ?, demand = ?, supply = ?, last_update = ?
                WHERE resource_type = ?""",
                (price, demand, supply, datetime.now(), resource_type),
            )

    def sell_resource(self, user_id: int, resource_type: str, quantity: float) -> float:
        resources = self.get_user_resources(user_id)
        if resources.get(resource_type, 0) < quantity:
            return 0

        prices = self.get_market_prices()
        if resource_type not in prices:
            return 0

        price = prices[resource_type]["current_price"]
        fee = price * quantity * config.MARKET_FEE
        earnings = price * quantity - fee

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """UPDATE user_resources 
                SET quantity = quantity - ? 
                WHERE user_id = ? AND resource_type = ?""",
                (quantity, user_id, resource_type),
            )
            cursor.execute(
                "UPDATE users SET balance = balance + ? WHERE user_id = ?",
                (earnings, user_id),
            )
            self.update_market_price(resource_type, supply_delta=quantity)

        return earnings

    def buy_resource(self, user_id: int, resource_type: str, amount: float) -> tuple:
        prices = self.get_market_prices()
        if resource_type not in prices:
            return False, "Ресурс не найден"

        price = prices[resource_type]["current_price"]
        cost = amount * price

        if self.get_balance(user_id) < cost:
            return False, f"Недостаточно средств. Нужно: ${cost:.2f}"

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE users SET balance = balance - ? WHERE user_id = ?",
                (cost, user_id),
            )
            cursor.execute(
                """INSERT INTO user_resources (user_id, resource_type, quantity)
                VALUES (?, ?, ?) ON CONFLICT(user_id, resource_type)
                DO UPDATE SET quantity = MIN(?, quantity + ?)""",
                (user_id, resource_type, amount, config.RESOURCE_MAX, amount),
            )
            self.update_market_price(resource_type, demand_delta=amount)

        return True, f"Куплено {amount} ед. за ${cost:.2f}"

    # ==================== ПЕРЕВОДЫ ====================

    def transfer_money(
        self, from_user: int, to_user: int, amount: float, chat_id: int = None
    ) -> tuple:
        if amount <= 0:
            return False, "Сумма должна быть положительной"

        fee = amount * config.TRANSFER_FEE
        total = amount + fee

        if self.get_balance(from_user) < total:
            return False, f"Недостаточно средств. Нужно: ${total:.2f}"

        if not self.get_user(to_user):
            return False, "Получатель не найден"

        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE users SET balance = balance - ? WHERE user_id = ?",
                    (total, from_user),
                )
                cursor.execute(
                    "UPDATE users SET balance = balance + ? WHERE user_id = ?",
                    (amount, to_user),
                )
                cursor.execute(
                    """INSERT INTO transactions (from_user, to_user, amount, fee, chat_id)
                    VALUES (?, ?, ?, ?, ?)""",
                    (from_user, to_user, amount, fee, chat_id),
                )
                return True, f"Переведено ${amount:.2f} (комиссия ${fee:.2f})"
        except Exception as e:
            return False, f"Ошибка: {e}"

    # ==================== ПРЕДМЕТЫ ====================

    def get_item(self, user_id: int, item_type: str) -> int:
        with self.get_connection() as conn:
            row = (
                conn.cursor()
                .execute(
                    "SELECT quantity FROM items WHERE user_id = ? AND item_type = ?",
                    (user_id, item_type),
                )
                .fetchone()
            )
            return row[0] if row else 0

    def add_item(self, user_id: int, item_type: str, quantity: int = 1):
        with self.get_connection() as conn:
            conn.cursor().execute(
                """INSERT INTO items (user_id, item_type, quantity)
                VALUES (?, ?, ?) ON CONFLICT(user_id, item_type)
                DO UPDATE SET quantity = quantity + ?""",
                (user_id, item_type, quantity, quantity),
            )

    def use_item(self, user_id: int, item_type: str) -> bool:
        if self.get_item(user_id, item_type) < 1:
            return False
        with self.get_connection() as conn:
            conn.cursor().execute(
                """UPDATE items SET quantity = quantity - 1
                WHERE user_id = ? AND item_type = ? AND quantity > 0""",
                (user_id, item_type),
            )
            return True

    # ==================== СОБЫТИЯ ====================

    def add_global_event(
        self,
        event_type: str,
        multiplier: float,
        affected_resource: str,
        message: str,
        hours: int = 24,
    ):
        with self.get_connection() as conn:
            conn.cursor().execute(
                """INSERT INTO global_events 
                (event_type, multiplier, affected_resource, message, starts_at, ends_at)
                VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    event_type,
                    multiplier,
                    affected_resource,
                    message,
                    datetime.now(),
                    datetime.now() + timedelta(hours=hours),
                ),
            )

    def get_active_events(self) -> List[sqlite3.Row]:
        with self.get_connection() as conn:
            return (
                conn.cursor()
                .execute(
                    """SELECT * FROM global_events 
                WHERE starts_at <= ? AND ends_at > ?""",
                    (datetime.now(), datetime.now()),
                )
                .fetchall()
            )

    def log_user_event(self, user_id: int, event_type: str, message: str):
        with self.get_connection() as conn:
            conn.cursor().execute(
                """INSERT INTO user_events (user_id, event_type, message)
                VALUES (?, ?, ?)""",
                (user_id, event_type, message),
            )

    # ==================== ЛИДЕРБОРД ====================

    def get_leaderboard(self, limit: int = 10) -> List[sqlite3.Row]:
        with self.get_connection() as conn:
            return (
                conn.cursor()
                .execute(
                    """SELECT user_id, username, balance FROM users
                ORDER BY balance DESC LIMIT ?""",
                    (limit,),
                )
                .fetchall()
            )

    # ==================== РЕФЕРАЛЫ ====================

    def get_referral_count(self, user_id: int) -> int:
        with self.get_connection() as conn:
            return (
                conn.cursor()
                .execute("SELECT COUNT(*) FROM referrals WHERE user_id = ?", (user_id,))
                .fetchone()[0]
            )

    def get_referrals(self, user_id: int) -> List[sqlite3.Row]:
        with self.get_connection() as conn:
            return (
                conn.cursor()
                .execute(
                    """SELECT r.*, u.username FROM referrals r
                JOIN users u ON r.referred_user_id = u.user_id WHERE r.user_id = ?""",
                    (user_id,),
                )
                .fetchall()
            )

    # ==================== ЧАТЫ ====================

    def add_chat(self, chat_id: int, chat_type: str, title: str = None):
        with self.get_connection() as conn:
            conn.cursor().execute(
                """INSERT OR IGNORE INTO chats (chat_id, chat_type, title)
                VALUES (?, ?, ?)""",
                (chat_id, chat_type, title),
            )

    def add_user_to_chat(self, chat_id: int, user_id: int):
        with self.get_connection() as conn:
            conn.cursor().execute(
                """INSERT OR IGNORE INTO chat_users (chat_id, user_id)
                VALUES (?, ?)""",
                (chat_id, user_id),
            )

    def get_chat_user(self, chat_id: int, user_id: int) -> Optional[sqlite3.Row]:
        with self.get_connection() as conn:
            return (
                conn.cursor()
                .execute(
                    "SELECT * FROM chat_users WHERE chat_id = ? AND user_id = ?",
                    (chat_id, user_id),
                )
                .fetchone()
            )

    # ==================== ПЕРЕВОДЫ С ЛИМИТОМ ====================

    DAILY_TRANSFER_LIMIT = 1000  # Лимит переводов в день

    def transfer_money(
        self, from_user: int, to_user: int, amount: float, chat_id: int = None
    ) -> tuple:
        if amount <= 0:
            return False, "Сумма должна быть положительной"

        fee = amount * config.TRANSFER_FEE
        total = amount + fee

        if self.get_balance(from_user) < total:
            return False, f"Недостаточно средств. Нужно: ${total:.2f}"

        if not self.get_user(to_user):
            return False, "Получатель не найден"

        # Проверка лимита переводов в чате
        if chat_id:
            chat_user = self.get_chat_user(chat_id, from_user)
            if chat_user:
                today = datetime.now().date().isoformat()
                daily_used = float(chat_user["daily_transfer_used"] or 0)
                last_reset = chat_user["last_transfer_reset"]

                # Сброс лимита если новый день
                if last_reset != today:
                    daily_used = 0

                if daily_used + amount > self.DAILY_TRANSFER_LIMIT:
                    remaining = self.DAILY_TRANSFER_LIMIT - daily_used
                    return False, f"Достигнут дневной лимит! Осталось: ${remaining:.2f}"

        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE users SET balance = balance - ? WHERE user_id = ?",
                    (total, from_user),
                )
                cursor.execute(
                    "UPDATE users SET balance = balance + ? WHERE user_id = ?",
                    (amount, to_user),
                )
                cursor.execute(
                    """INSERT INTO transactions (from_user, to_user, amount, fee, chat_id)
                    VALUES (?, ?, ?, ?, ?)""",
                    (from_user, to_user, amount, fee, chat_id),
                )

                # Обновляем дневной лимит
                if chat_id:
                    today = datetime.now().date().isoformat()
                    cursor.execute(
                        """UPDATE chat_users SET daily_transfer_used = ?, last_transfer_reset = ?
                        WHERE chat_id = ? AND user_id = ?""",
                        (daily_used + amount, today, chat_id, from_user),
                    )

                # Логирование
                cursor.execute(
                    """INSERT INTO action_logs (user_id, action_type, details)
                    VALUES (?, 'transfer', ?)""",
                    (from_user, f"To {to_user}: ${amount} (fee: ${fee:.2f})"),
                )

                return True, f"Переведено ${amount:.2f} (комиссия ${fee:.2f})"
        except Exception as e:
            return False, f"Ошибка: {e}"

    # ==================== ЛОТЕРЕЯ ====================

    LOTTERY_COST_REGULAR = 10  # $10
    LOTTERY_COST_PREMIUM = 2  # Stars
    LOTTERY_CHANCES = {
        0: 0.70,  # 70% проигрыш
        1.5: 0.25,  # 25% x1.5
        3: 0.04,  # 4% x3
        10: 0.01,  # 1% x10
    }

    def play_lottery(
        self, user_id: int, chat_id: int = None, is_premium: bool = False
    ) -> dict:
        """Играть в лотерею. Возвращает результат."""
        cost = self.LOTTERY_COST_PREMIUM if is_premium else self.LOTTERY_COST_REGULAR

        # Списываем стоимость (для премиум - Stars, для обычной - деньги)
        if is_premium:
            # TODO: Проверка Stars
            pass
        else:
            if self.get_balance(user_id) < cost:
                return {
                    "won": False,
                    "won_amount": 0,
                    "multiplier": 0,
                    "message": f"Недостаточно средств! Нужно ${cost}",
                }
            self.update_balance(user_id, -cost)

        # Генерируем случайный результат
        roll = random.random()
        cumulative = 0
        multiplier = 0

        for mult, chance in self.LOTTERY_CHANCES.items():
            cumulative += chance
            if roll < cumulative:
                multiplier = mult
                break

        won_amount = cost * multiplier if multiplier > 0 else 0

        # Начисляем выигрыш
        if won_amount > 0:
            self.update_balance(user_id, won_amount)

        # Записываем в лог лотереи
        with self.get_connection() as conn:
            conn.cursor().execute(
                """INSERT INTO lottery (user_id, chat_id, ticket_type, stake, multiplier)
                VALUES (?, ?, ?, ?, ?)""",
                (
                    user_id,
                    chat_id,
                    "premium" if is_premium else "regular",
                    cost,
                    multiplier,
                ),
            )

        # Логирование
        self.log_action(
            user_id,
            "lottery",
            f"Stake: ${cost}, Multiplier: x{multiplier}, Won: ${won_amount}",
        )

        return {
            "won": multiplier > 0,
            "won_amount": won_amount,
            "multiplier": multiplier,
            "message": self._get_lottery_message(multiplier, won_amount, is_premium),
        }

    def _get_lottery_message(
        self, multiplier: float, won_amount: float, is_premium: bool
    ) -> str:
        if multiplier == 0:
            return "😢 <b>Не повезло!</b>\n\nТы проиграл, но не сдавайся!"
        elif multiplier == 1.5:
            return (
                f"🎉 <b>Почти!</b>\n\nx{multiplier} — твой выигрыш: ${won_amount:.2f}"
            )
        elif multiplier == 3:
            return (
                f"💰 <b>КРУТО!</b>\n\nx{multiplier} — твой выигрыш: ${won_amount:.2f}"
            )
        else:
            return (
                f"🎊 <b>ДЖЕКПОТ!</b>\n\nx{multiplier} — твой выигрыш: ${won_amount:.2f}"
            )

    def get_lottery_stats(self, user_id: int) -> dict:
        """Статистика лотереи игрока"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Всего игр
            cursor.execute("SELECT COUNT(*) FROM lottery WHERE user_id = ?", (user_id,))
            total_games = cursor.fetchone()[0]

            # Выигрышей
            cursor.execute(
                "SELECT COUNT(*) FROM lottery WHERE user_id = ? AND multiplier > 0",
                (user_id,),
            )
            wins = cursor.fetchone()[0]

            # Общий выигрыш
            cursor.execute(
                "SELECT SUM(stake * multiplier) FROM lottery WHERE user_id = ? AND multiplier > 0",
                (user_id,),
            )
            total_won = cursor.fetchone()[0] or 0

            # Общие потери
            cursor.execute(
                "SELECT SUM(stake) FROM lottery WHERE user_id = ? AND multiplier = 0",
                (user_id,),
            )
            total_lost = cursor.fetchone()[0] or 0

            return {
                "games": total_games,
                "wins": wins,
                "losses": total_games - wins,
                "total_won": total_won,
                "total_lost": total_lost,
                "win_rate": (wins / total_games * 100) if total_games > 0 else 0,
            }

    # ==================== ЛОГИРОВАНИЕ ====================

    def log_action(self, user_id: int, action_type: str, details: str):
        with self.get_connection() as conn:
            conn.cursor().execute(
                """INSERT INTO action_logs (user_id, action_type, details)
                VALUES (?, ?, ?)""",
                (user_id, action_type, details),
            )

    def get_user_actions(self, user_id: int, limit: int = 20) -> List[sqlite3.Row]:
        with self.get_connection() as conn:
            return (
                conn.cursor()
                .execute(
                    """SELECT * FROM action_logs
                WHERE user_id = ? ORDER BY created_at DESC LIMIT ?""",
                    (user_id, limit),
                )
                .fetchall()
            )

    # ==================== ЧАТЫ И УРОВНИ ====================

    def get_chat(self, chat_id: int) -> Optional[sqlite3.Row]:
        with self.get_connection() as conn:
            return (
                conn.cursor()
                .execute("SELECT * FROM chats WHERE chat_id = ?", (chat_id,))
                .fetchone()
            )

    def create_or_update_chat(
        self, chat_id: int, chat_type: str, title: str = None, added_by: int = None
    ) -> bool:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO chats (chat_id, chat_type, title, added_by_user_id)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(chat_id) DO UPDATE SET
                title = COALESCE(excluded.title, title)
            """,
                (chat_id, chat_type, title, added_by),
            )
            return True

    def add_chat_xp(self, chat_id: int, xp: int) -> tuple:
        """Добавить XP чату. Возвращает (success, leveled_up, new_level)"""
        chat = self.get_chat(chat_id)
        if not chat:
            return False, False, 0

        current_xp = chat["xp"]
        current_level = chat["level"]
        new_xp = current_xp + xp

        # Формула для уровня: level_up_xp = 100 * level^1.5
        xp_needed = int(100 * (current_level**1.5))

        # Проверяем повышение уровня
        if new_xp >= xp_needed:
            new_level = current_level + 1
            with self.get_connection() as conn:
                conn.cursor().execute(
                    """
                    UPDATE chats SET xp = ?, level = ? WHERE chat_id = ?
                """,
                    (new_xp - xp_needed, new_level, chat_id),
                )
            # Выдаём награду всем участникам чата
            self.reward_chat_users(chat_id, config.CHAT_LEVEL_UP_ENERGY_BONUS)
            return True, True, new_level

        with self.get_connection() as conn:
            conn.cursor().execute(
                "UPDATE chats SET xp = ? WHERE chat_id = ?", (new_xp, chat_id)
            )

        return True, False, current_level

    def get_xp_needed_for_level(self, level: int) -> int:
        """Рассчитать XP для следующего уровня"""
        return int(100 * (level**1.5))

    def get_chat_bonus(self, chat_id: int) -> dict:
        """Получить бонусы чата в зависимости от уровня"""
        chat = self.get_chat(chat_id)
        if not chat:
            return {
                "income_bonus": 0,
                "energy_discount": 0,
                "jackpot_chance_bonus": 0,
                "free_tickets": 0,
            }

        level = chat["level"]
        bonuses = {
            "income_bonus": 0,
            "energy_discount": 0,
            "jackpot_chance_bonus": 0,
            "free_tickets": 0,
        }

        if level >= 2:
            bonuses["income_bonus"] = 0.05
        if level >= 3:
            bonuses["free_tickets"] = 1
        if level >= 4:
            bonuses["energy_discount"] = 0.10
        if level >= 5:
            bonuses["jackpot_chance_bonus"] = 0.10

        return bonuses

    def get_top_chats(self, limit: int = 10) -> List[sqlite3.Row]:
        """Получить топ чатов по уровню"""
        with self.get_connection() as conn:
            return (
                conn.cursor()
                .execute(
                    """
                SELECT chat_id, title, level, xp FROM chats
                ORDER BY level DESC, xp DESC LIMIT ?
            """,
                    (limit,),
                )
                .fetchall()
            )

    def has_claimed_bonus(self, chat_id: int) -> bool:
        """Проверить получал ли чат бонус за добавление"""
        chat = self.get_chat(chat_id)
        return chat["bonus_claimed"] == 1 if chat else False

    def claim_chat_bonus(self, chat_id: int) -> bool:
        """Отметить что бонус за добавление чата получен"""
        with self.get_connection() as conn:
            conn.cursor().execute(
                "UPDATE chats SET bonus_claimed = 1 WHERE chat_id = ?", (chat_id,)
            )
        return True

    # ==================== ПЛАТЕЖИ (TELEGRAM STARS) ====================

    def create_payment(
        self, user_id: int, item_type: str, stars_amount: int, chat_id: int = None
    ) -> int:
        """Создать платёж. Возвращает payment_id"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO payments (user_id, chat_id, item_type, stars_amount, status)
                VALUES (?, ?, ?, ?, 'pending')
            """,
                (user_id, chat_id, item_type, stars_amount),
            )
            return cursor.lastrowid

    def complete_payment(self, payment_id: int) -> bool:
        """Отметить платёж как завершённый"""
        with self.get_connection() as conn:
            conn.cursor().execute(
                "UPDATE payments SET status = 'completed' WHERE id = ?", (payment_id,)
            )
        return True

    def cancel_payment(self, payment_id: int) -> bool:
        """Отменить платёж"""
        with self.get_connection() as conn:
            conn.cursor().execute(
                "UPDATE payments SET status = 'cancelled' WHERE id = ?", (payment_id,)
            )
        return True

    def get_payment(self, payment_id: int) -> Optional[sqlite3.Row]:
        """Получить информацию о платеже"""
        with self.get_connection() as conn:
            return (
                conn.cursor()
                .execute("SELECT * FROM payments WHERE id = ?", (payment_id,))
                .fetchone()
            )

    def set_chat_vip(self, chat_id: int, days: int = 7) -> bool:
        """Установить VIP статус для чата"""
        try:
            with self.get_connection() as conn:
                from datetime import datetime, timedelta
                expire = datetime.now() + timedelta(days=days)
                conn.cursor().execute(
                    "UPDATE chats SET vip_status = 1, vip_expire = ? WHERE chat_id = ?",
                    (expire, chat_id),
                )
                return True
        except Exception as e:
            print(f"Error setting chat VIP: {e}")
            return False

    def is_chat_vip(self, chat_id: int) -> bool:
        """Проверить является ли чат VIP"""
        chat = self.get_chat(chat_id)
        if not chat or not chat["vip_status"]:
            return False
        if chat["vip_expire"]:
            from datetime import datetime
            return datetime.fromisoformat(chat["vip_expire"]) > datetime.now()
        return False

    def get_chat_vip_bonus(self, chat_id: int) -> dict:
        """Получить VIP бонусы чата"""
        if self.is_chat_vip(chat_id):
            return {
                "xp_bonus": 0.10,  # +10% к получению XP
                "income_bonus": 0.05,  # +5% к доходу
            }
        return {
            "xp_bonus": 0,
            "income_bonus": 0,
        }

    def get_chat_users(self, chat_id: int) -> List[sqlite3.Row]:
        """Получить всех пользователей чата"""
        with self.get_connection() as conn:
            return (
                conn.cursor()
                .execute("SELECT user_id FROM chat_users WHERE chat_id = ?", (chat_id,))
                .fetchall()
            )

    def reward_chat_users(self, chat_id: int, energy_bonus: int):
        """Выдать награду всем пользователям чата"""
        from services.energy import EnergyService
        
        users = self.get_chat_users(chat_id)
        for user_row in users:
            user_id = user_row["user_id"]
            EnergyService.add_energy(user_id, energy_bonus)


    # ==================== ДЖЕКПОТ ====================

    def get_jackpot_bank(self) -> float:
        with self.get_connection() as conn:
            row = conn.cursor().execute("SELECT amount FROM jackpot_bank WHERE id=1").fetchone()
            return float(row["amount"]) if row else 0.0

    def add_to_jackpot_bank(self, amount: float):
        with self.get_connection() as conn:
            conn.cursor().execute(
                "UPDATE jackpot_bank SET amount = amount + ?, updated_at = CURRENT_TIMESTAMP WHERE id=1",
                (amount,)
            )

    def reset_jackpot_pool(self):
        with self.get_connection() as conn:
            conn.cursor().execute("UPDATE jackpot_bank SET amount = 0.0, last_draw = CURRENT_TIMESTAMP WHERE id=1")
            conn.cursor().execute("UPDATE jackpot_tickets SET tickets = 0")

    def add_jackpot_tickets(self, user_id: int, count: int = 1):
        with self.get_connection() as conn:
            conn.cursor().execute(
                """INSERT INTO jackpot_tickets (user_id, tickets) VALUES (?, ?)
                   ON CONFLICT(user_id) DO UPDATE SET tickets = tickets + ?, updated_at = CURRENT_TIMESTAMP""",
                (user_id, count, count)
            )

    def use_jackpot_ticket(self, user_id: int):
        with self.get_connection() as conn:
            conn.cursor().execute(
                """UPDATE jackpot_tickets SET tickets = MAX(0, tickets - 1),
                   first_used = 1, updated_at = CURRENT_TIMESTAMP WHERE user_id = ?""",
                (user_id,)
            )

    def has_used_first_ticket(self, user_id: int) -> bool:
        with self.get_connection() as conn:
            row = conn.cursor().execute(
                "SELECT first_used FROM jackpot_tickets WHERE user_id=?", (user_id,)
            ).fetchone()
            return bool(row and row["first_used"])

    def get_jackpot_tickets(self, user_id: int) -> int:
        with self.get_connection() as conn:
            row = conn.cursor().execute(
                "SELECT tickets FROM jackpot_tickets WHERE user_id=?", (user_id,)
            ).fetchone()
            return int(row["tickets"]) if row else 0

    def get_jackpot_participants(self) -> list:
        with self.get_connection() as conn:
            rows = conn.cursor().execute(
                "SELECT user_id, tickets FROM jackpot_tickets WHERE tickets > 0"
            ).fetchall()
            return [{"user_id": r["user_id"], "tickets": r["tickets"]} for r in rows]

    def get_last_jackpot_draw(self):
        with self.get_connection() as conn:
            row = conn.cursor().execute("SELECT last_draw FROM jackpot_bank WHERE id=1").fetchone()
            if row and row["last_draw"]:
                from datetime import datetime
                try:
                    return datetime.fromisoformat(row["last_draw"])
                except Exception:
                    return None
            return None

    def set_jackpot_draw_time(self):
        with self.get_connection() as conn:
            conn.cursor().execute("UPDATE jackpot_bank SET last_draw = CURRENT_TIMESTAMP WHERE id=1")

    # ==================== КРЕДИТЫ ====================

    def create_credit(self, user_id: int, credit_type: str, amount: float, repay: float, due_time) -> int:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO credits (user_id, credit_type, amount, repay_amount, due_time)
                   VALUES (?, ?, ?, ?, ?)""",
                (user_id, credit_type, amount, repay, due_time.isoformat())
            )
            return cursor.lastrowid

    def get_active_credit(self, user_id: int):
        with self.get_connection() as conn:
            return conn.cursor().execute(
                "SELECT * FROM credits WHERE user_id=? AND status='active' ORDER BY created_at DESC LIMIT 1",
                (user_id,)
            ).fetchone()

    def pay_credit(self, user_id: int, credit_id: int, amount: float):
        with self.get_connection() as conn:
            conn.cursor().execute(
                "UPDATE credits SET paid_amount = paid_amount + ? WHERE id=? AND user_id=?",
                (amount, credit_id, user_id)
            )

    def close_credit(self, user_id: int, credit_id: int):
        with self.get_connection() as conn:
            conn.cursor().execute(
                "UPDATE credits SET status='closed' WHERE id=? AND user_id=?",
                (credit_id, user_id)
            )

    def get_overdue_credits(self) -> list:
        with self.get_connection() as conn:
            rows = conn.cursor().execute(
                "SELECT * FROM credits WHERE status='active' AND due_time < CURRENT_TIMESTAMP"
            ).fetchall()
            return [dict(zip([d[0] for d in rows.description if rows.description], r)) for r in rows] if rows else []

    def add_credit_debt(self, credit_id: int, amount: float):
        with self.get_connection() as conn:
            conn.cursor().execute(
                "UPDATE credits SET repay_amount = repay_amount + ? WHERE id=?",
                (amount, credit_id)
            )

    def reduce_credit_debt(self, credit_id: int, amount: float):
        with self.get_connection() as conn:
            conn.cursor().execute(
                "UPDATE credits SET repay_amount = MAX(0, repay_amount - ?) WHERE id=?",
                (amount, credit_id)
            )

    def remove_business(self, user_id: int, biz_id: int):
        with self.get_connection() as conn:
            conn.cursor().execute(
                "DELETE FROM businesses WHERE id=? AND user_id=?",
                (biz_id, user_id)
            )

    def get_users_with_overdue_credits(self) -> list:
        with self.get_connection() as conn:
            rows = conn.cursor().execute(
                """SELECT DISTINCT c.user_id FROM credits c
                   WHERE c.status='active' AND c.due_time < CURRENT_TIMESTAMP"""
            ).fetchall()
            return [r["user_id"] for r in rows]

    def give_starting_ticket(self, user_id: int):
        self.add_jackpot_tickets(user_id, 1)


db = Database()
