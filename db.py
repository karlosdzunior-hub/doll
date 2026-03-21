"""
Database module - работа с базой данных (Production с энергией)
"""

import sqlite3
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

            # Индексы
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
                        float(config.MAX_ENERGY),
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


db = Database()
