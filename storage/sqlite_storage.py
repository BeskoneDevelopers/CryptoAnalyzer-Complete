import sqlite3

from .base import BaseStorage


class SqliteStorage(BaseStorage):

    def __init__(self, db_path: str = "crypto_analysis.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)

        self.conn.execute("PRAGMA foreign_keys = ON")

        self._init_db()

    def _init_db(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS cadr (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                generated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                provider TEXT NOT NULL,
                total_coins INTEGER NOT NULL,
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
                FOREIGN KEY (cadr_id)
                    REFERENCES cadr(id)
                    ON DELETE CASCADE
            )
        """)

        self.conn.commit()

    def save(self, data: dict):
        cursor = self.conn.execute(
            """
            INSERT INTO cadr (
                generated_at,
                provider,
                total_coins,
                total_market_cap
            )
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
                coin.get("24h_change"),
            ))

        self.conn.executemany(
            """
            INSERT INTO coin_price (
                cadr_id,
                name,
                symbol,
                price,
                volume_24h,
                "24h_change"
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            coin_rows
        )

        self.conn.commit()

    def list_cadr(self):
        rows = self.conn.execute(
            """
            SELECT
                id,
                generated_at,
                provider,
                total_coins,
                total_market_cap
            FROM cadr
            ORDER BY generated_at DESC
            """
        ).fetchall()

        return rows

    def compare_cadr(self, id1: int, id2: int):
        rows = self.conn.execute(
            """
            SELECT
                a.symbol,
                a.price AS old_price,
                b.price AS new_price,
                (b.price - a.price) AS diff
            FROM coin_price a
            JOIN coin_price b
                ON a.symbol = b.symbol
            WHERE a.cadr_id = ?
              AND b.cadr_id = ?
              AND a.price IS NOT NULL
              AND b.price IS NOT NULL
            GROUP BY a.symbol
            """,
            (id1, id2)
        ).fetchall()

        return rows

    def _get_top_last(self, limit: int, direction: str):
        if direction not in {"ASC", "DESC"}:
            raise ValueError(f"Некорректное направление сортировки: {direction}")

        rows = self.conn.execute(
            f"""
            SELECT name, symbol, price, "24h_change"
            FROM coin_price
            WHERE cadr_id = (
                SELECT MAX(id)
                FROM cadr
            )
            ORDER BY "24h_change" {direction}
            LIMIT ?
            """,
            (limit,)
        ).fetchall()

        return rows

    def get_top_gainers_last(self, limit: int = 5):
        return self._get_top_last(limit, "DESC")

    def get_top_loser_last(self, limit: int = 5):
        return self._get_top_last(limit, "ASC")


    def get_coin_history(self, symbol: str):
        rows = self.conn.execute(
            """
            SELECT
                c.generated_at,
                p.price,
                p."24h_change"
            FROM coin_price p
            JOIN cadr c ON p.cadr_id = c.id
            WHERE p.symbol = ?
            ORDER BY c.generated_at
            """,
            (symbol,)
        ).fetchall()

        return rows

    def close(self):
        if self.conn:
            self.conn.close()
            self.conn = None