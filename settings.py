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
        self.storage = StorageType(storage_str)

settings = Settings()