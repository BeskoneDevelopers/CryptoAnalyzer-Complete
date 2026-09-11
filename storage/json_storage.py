import json

from .base import BaseStorage


class JsonStorage(BaseStorage):

    def __init__(self, filename: str = "crypto_report.json"):
        self.filename = filename

    def save(self, data: dict):
        with open(self.filename, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

    def list_cadr(self):
        raise NotImplementedError(
            "Команда list-cadr доступна только для SQLite"
        )

    def compare_cadr(self, id1: int, id2: int):
        raise NotImplementedError(
            "Команда compare-cadr доступна только для SQLite"
        )