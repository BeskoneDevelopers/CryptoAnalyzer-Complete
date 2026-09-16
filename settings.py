import os
from enum import Enum

from dotenv import load_dotenv


load_dotenv()


class StorageType(Enum):
    JSON = "json"
    SQLITE = "sqlite"


class Settings:
    def __init__(self):
        storage_str = os.getenv("STORAGE", "json")

        try:
            self.storage = StorageType(storage_str)
        except ValueError:
            allowed = ", ".join(storage.value for storage in StorageType)

            raise ValueError(
                f"Неизвестный тип хранилища: {storage_str}. "
                f"Допустимые значения: {allowed}"
            )

settings = Settings()