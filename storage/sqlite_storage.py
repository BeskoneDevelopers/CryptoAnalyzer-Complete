import sqlite3
from .base import BaseStorage

class SqliteStorage(BaseStorage):

    def __init__(self, db_path: str = "crypto_analysis.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        print(f"DB path: {self.db_path}")
        self._init_db()
        print("Tables created")

    def _init_db(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS cadr (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            generated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            provider TEXT NOT NULL,
            total_coins FLOAT NOT NULL,
            total_market_cap FLOAT NOT NULL
            )
        """)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS coin_price (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cadr_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            symbol TEXT NOT NULL,
            price FLOAT,
            volume_24h FLOAT,
            "24h_change" FLOAT,
            FOREIGN KEY (cadr_id) REFERENCES cadr(id) ON DELETE CASCADE
            )
        """)
        self.conn.commit()

    def save(self, data: dict):
        cursor = self.conn.execute(
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

        self.conn.executemany(
            """
            INSERT INTO coin_price (cadr_id, name, symbol, price, volume_24h, "24h_change")
            VALUES (?,?,?,?,?,?)
            """,
            coin_rows
        )

    def list_cadr(self):
        rows = self.conn.execute(
            """
            SELECT id, generated_at, provider, total_coins, total_market_cap
            FROM cadr
            ORDER BY generated_at DESC
            """
        ).fetchall()
        return rows

    def compare_cadr(self, id1: int, id2):
        rows = self.conn.execute(
            """
            SELECT a.symbol, a.price as old_price, b.price as new_price, (b.price - a.price) as diff
            FROM coin_price a JOIN coin_price b ON a.symbol = b.symbol
            WHERE a.cadr_id = ? AND b.cadr_id = ?
            """,
            (id1, id2)
        ).fetchall()
        return rows

    def get_top_gainers_last(self, limit: int = 5):
        rows = self.conn.execute(
            """
            SELECT name, symbol, price, "24h_change"
            FROM coin_price
            WHERE cadr_id = (SELECT MAX(id) FROM cadr)
            ORDER BY "24h_change" DESC
            LIMIT ?
            """,
            (limit,)
        ).fetchall()
        return rows

    def get_top_loser_last(self, limit: int = 5):
        rows = self.conn.execute(
            """
            SELECT name, symbol, price, "24h_change"
            FROM coin_price
            WHERE cadr_id = (SELECT MAX(id) FROM cadr)
            ORDER BY "24h_change" ASC
            LIMIT ?
            """,
            (limit,)
         ).fetchall()
        return rows

    def get_coin_history(self, symbol: str):
        rows = self.conn.execute(
            """
            SELECT c.generated_at, p.price, p."24h_change"
            FROM coin_price p JOIN cadr c ON p.cadr_id = c.id
            WHERE p.symbol = ?
            ORDER BY c.generated_at
            """,
            (symbol,)
        ).fetchall()
        return rows

    def close(self):
        self.conn.close()