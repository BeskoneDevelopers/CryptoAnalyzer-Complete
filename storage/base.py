from abc import ABC, abstractmethod

class BaseStorage(ABC):
    @abstractmethod
    def save(self, data: dict):
        pass

    @abstractmethod
    def list_cadr(self):
        pass

    @abstractmethod
    def compare_cadr(self, id1: int, id2: int):
        pass

    def close(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()