import sqlite3
from .base import BaseStorage

class SqliteStorage(BaseStorage):

    def __init__(self, db_path: str = "crypto_analysis.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cadr (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                generated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                provider TEXT NOT NULL,
                total_coins FLOAT NOT NULL,
                total_market_cap FLOAT NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS coin_price (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cadr_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                symbol TEXT NOT NULL,
                price FLOAT,
                volume_24h FLOAT,
                24h_change FLOAT,
                FOREIGN KEY (cadr_id) REFERENCES cadr(id) ON DELETE CASCADE
                )
            """)

    def save(self, data: dict):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                INSERT INTO cadr (generated_at, provider, total_coins, total_market_cap)
                VALUES (?, ?, ?, ?)
                """,
                (
                    data["generated_at"],
                    data["provider"],
                    data["total_coins"],
                    data["total_market_cap"],
                )
            )
            cadr_id = cursor.lastrowid

            coin_rows = []
            for coin in data["all_coins"]:
                coin_rows.append((
                    cadr_id,
                    coin["name"],
                    coin["symbol"],
                    coin.get("price"),
                    coin.get("volume_24h"),
                    coin.get("24h_change")

                ))

            conn.executemany(
                """
                INSERT INTO coin_price (cadr_id, name, symbol, price, volume_24h, 24h_change)
                VALUES (?,?,?,?,?,?)
                """,
                coin_rows
            )