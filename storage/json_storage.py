import json
from .base import BaseStorage

class JsonStorage(BaseStorage):
    def __init__(self, filename: str = "crypto_reporter.json"):
        self.filename = filename

    def save(self, data: dict):
        with open(self.filename, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        print(f"Файл сохранен - {self.filename}")