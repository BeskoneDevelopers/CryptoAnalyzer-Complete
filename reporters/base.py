from abc import ABC, abstractmethod
from datetime import datetime
from models.portfolio import CryptoPortfolio

class BaseReporter(ABC):

    def __init__(self):
        self.generate_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    @abstractmethod
    def report(self, portfolio: CryptoPortfolio, provider_name: str, top_count: int = 3) -> None:
        pass