from .base import BaseReporter
from .console import ConsoleReporter
from .json_reporter import JsonReporter
from .csv_reporter import CsvReporter

def get_reporter(output: str) -> BaseReporter:
    if output == "console":
        return ConsoleReporter()
    elif output == "json":
        return JsonReporter()
    elif output == "csv":
        return CsvReporter
    else:
        raise ValueError(f"Неизвестный формат - {output}")