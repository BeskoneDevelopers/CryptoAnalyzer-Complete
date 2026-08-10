import csv

from .base import BaseReporter
from models.portfolio import CryptoPortfolio

class CsvReporter(BaseReporter):

    def __init__(self, filename: str = "crypto_report.csv"):
        super().__init__()
        self.filename = filename

    def report(self, portfolio: CryptoPortfolio, provider_name: str, top_count: int = 3) -> None:

        gainers = portfolio.get_top_gainers(top_count)
        losers = portfolio.get_top_losers(top_count)
        highest = portfolio.get_highest_volume()

        with open(self.filename, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)

            writer.writerow(["Crypto Market Analysis"])
            writer.writerow([f"Generated: {self.generate_at}]"])
            writer.writerow([f"Provider: {provider_name}"])
            writer.writerow([])

            writer.writerow(["Top Gainers"])
            writer.writerow(["Name", "Symbol", "Price", "24h Change"])
            for coin in gainers:
                price = f"{coin.current_price:,.2f}" if coin.current_price is not None else "Данных нет"
                change = f"+{coin.price_change_for_24h:.2f}%" if coin.price_change_for_24h is not None else "Данных нет"
                writer.writerow([coin.name, coin.symbol, price, change])
            writer.writerow([])

            writer.writerow(["Top Losers"])
            writer.writerow(["Name", "Symbol", "Price", "24h Change"])
            for coin in losers:
                price = f"${coin.current_price:,.2f}" if coin.current_price else "Данных нет"
                change = f"{coin.price_change_for_24h:.2f}%" if coin.price_change_for_24h else "Данных нет"
                writer.writerow([coin.name, coin.symbol, price, change])
            writer.writerow([])

            writer.writerow(["Summary"])
            writer.writerow(["Total coins", len(portfolio)])
            writer.writerow(["Total Market Cap", f"{portfolio.get_total_market_cap():,.0f}"])
            if highest:

                writer.writerow(["Highest Volume", f"{highest.name} ({highest.symbol})"])
            print(f"Файл сохранен - {self.filename}")