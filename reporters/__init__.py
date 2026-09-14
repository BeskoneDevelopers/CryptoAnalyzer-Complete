from .base import BaseReporter
from .console import ConsoleReporter
from .json_reporter import JsonReporter
from .csv_reporter import CsvReporter

from storage.base import BaseStorage

def get_reporter(output: str, storage: BaseStorage = None) -> BaseReporter:
    if output == "console":
        return ConsoleReporter()
    elif output == "json":
        return JsonReporter(storage=storage)
    elif output == "csv":
        return CsvReporter()
    else:
        raise ValueError(f"Неизвестный формат - {output}")