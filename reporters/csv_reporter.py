import csv

from .base import BaseReporter


class CsvReporter(BaseReporter):

    def __init__(self, filename: str = "crypto_report.csv"):
        super().__init__()
        self.filename = filename

    def report(self, data: dict) -> None:
        with open(self.filename, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)

            writer.writerow(["Crypto Market Analysis"])
            writer.writerow([f"Generated: {data['generated_at']}"])
            writer.writerow([f"Provider: {data['provider']}"])
            writer.writerow([])

            writer.writerow(["Top Gainers"])
            writer.writerow(["Name", "Symbol", "Price", "24h Change"])

            for coin in data["top_gainers"]:
                price = (
                    f"${coin['price']:,.2f}"
                    if coin["price"] is not None
                    else "Данных нет"
                )
                change = (
                    f"{coin['24h_change']:+.2f}%"
                    if coin["24h_change"] is not None
                    else "Данных нет"
                )

                writer.writerow([
                    coin["name"],
                    coin["symbol"],
                    price,
                    change,
                ])

            writer.writerow([])

            writer.writerow(["Top Losers"])
            writer.writerow(["Name", "Symbol", "Price", "24h Change"])

            for coin in data["top_losers"]:
                price = (
                    f"${coin['price']:,.2f}"
                    if coin["price"] is not None
                    else "Данных нет"
                )
                change = (
                    f"{coin['24h_change']:+.2f}%"
                    if coin["24h_change"] is not None
                    else "Данных нет"
                )

                writer.writerow([
                    coin["name"],
                    coin["symbol"],
                    price,
                    change,
                ])

            writer.writerow([])

            writer.writerow(["Summary"])
            writer.writerow(["Total coins", data["total_coins"]])
            writer.writerow([
                "Total Market Cap",
                f"{data['total_market_cap']:,.0f}",
            ])

            highest = data["highest_volume"]
            if highest:
                writer.writerow([
                    "Highest Volume",
                    f"{highest['name']} ({highest['symbol']})",
                ])

        print(f"Файл сохранен - {self.filename}")