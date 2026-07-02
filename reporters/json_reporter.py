import json

from .base import BaseReporter
from models.portfolio import CryptoPortfolio

class JsonReporter(BaseReporter):

    def __init__(self, filename: str = "crypto_report.json"):
        super().__init__()
        self.filename = filename
        
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
            "highest_volume": {
                "name": highest.name,
                "symbol": highest.symbol,
                "volume": highest.total_value
            }
        }
        
        with open(self.filename, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

        print(f"Файл сохранен - {self.filename}")