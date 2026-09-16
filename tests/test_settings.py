import pytest
from settings import Settings, StorageType

def test_settings_invalid_storage(monkeypatch):
    monkeypatch.setenv("STORAGE", "postgres")

    with pytest.raises(
        ValueError,
        match="Допустимые значения: json, sqlite",
    ):
        Settings()


def test_settings_sqlite_storage(monkeypatch):
    monkeypatch.setenv("STORAGE", "sqlite")
    settings = Settings()
    assert settings.storage == StorageType.SQLITE