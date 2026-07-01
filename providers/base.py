from abc import ABC, abstractmethod
from typing import List
from models.coin import Coin

class BaseProvider(ABC):

    @abstractmethod
    def featch_top_coins(self, limit: int = 50) -> List[Coin]:
        pass

    @abstractmethod
    def get_name(self) -> str:
        pass