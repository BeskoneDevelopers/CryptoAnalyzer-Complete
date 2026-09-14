import json

from .base import BaseReporter
from models.portfolio import CryptoPortfolio

from storage.base import BaseStorage
from storage.json_storage import JsonStorage

class JsonReporter(BaseReporter):

    def __init__(self, storage: BaseStorage = None, filename: str = "crypto_report.json"):
        super().__init__()
        self.storage = storage or JsonStorage(filename)
        
    def report(self, portfolio: CryptoPortfolio, provider_name: str, top_count: int = 3) -> None:
        gainers = portfolio.get_top_gainers(top_count)
        losers = portfolio.get_top_losers(top_count)
        highest = portfolio.get_highest_volume()
        
        data = {
            "generated_at": self.generate_at,
            "provider": provider_name,
            "total_coins": len(portfolio),
            "total_market_cap": portfolio.get_total_market_cap(),
            "top_gainers": [
                {"name": coin.name, "symbol": coin.symbol, "price": coin.current_price, "24h_change": coin.price_change_for_24h}
                for coin in gainers
            ],
            "top_losers": [
                {"name": coin.name, "symbol": coin.symbol, "price": coin.current_price,
                 "24h_change": coin.price_change_for_24h}
                for coin in losers
            ],
            "all_coins" : [
                {
                    "name": coin.name,
                    "symbol": coin.symbol,
                    "price": coin.current_price,
                    "volume_24h": coin.total_volume,
                    "24h_change": coin.price_change_for_24h
                }
                for coin in portfolio
            ],
            "highest_volume": {
                "name": highest.name,
                "symbol": highest.symbol,
                "volume": highest.total_volume
            }

        }
        
        self.storage.save(data)