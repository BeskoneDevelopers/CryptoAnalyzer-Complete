import json

from .base import BaseReporter


class JsonReporter(BaseReporter):

    def __init__(self, filename: str = "crypto_report.json"):
        super().__init__()
        self.filename = filename

    def report(self, data: dict) -> None:
        with open(self.filename, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

        print(f"Файл сохранен - {self.filename}")