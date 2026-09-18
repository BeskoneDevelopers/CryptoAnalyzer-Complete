from django.core.management.base import BaseCommand, CommandError
from analyzer.models import Coin, Snapshot, CoinPrice
from django.conf import settings

from analyzer.tasks import fetch_snapshot_task

class Command(BaseCommand):
    help = "Извлекает крипто-данные и создает снимок"

    def add_arguments(self, parser):
        parser.add_argument("--provider", type=str, default="coingecko")
        parser.add_argument("--limit", type=int, default=10)

    def handle(self, *args, **options):
        provider = options["provider"]
        limit = options["limit"]

        task = fetch_snapshot_task.delay(provider, limit)
        self.stdout.write(f"Операция создана: {task.id}")

    def fetch_data(self, provider, limit):
        if provider == "coingecko":
            url = "https://api.coingecko.com/api/v3/coins/markets"
            params = {
                "vs_currency": "usd",
                "order": "market_cap_desc",
                "per_page": limit,
                "page": 1
            }
            with requests.Session() as session:
                response = session.get(url, params=params)
                response.raise_for_status()
                raw_data = response.json()
                normalized = []
                for item in raw_data:
                    normalized.append({
                        "name": item["name"],
                        "symbol": item["symbol"],
                        "current_price": item["current_price"],
                        "total_volume": item["total_volume"],
                        "price_change_percentage_24h": item.get("price_change_percentage_24h"),
                        "market_cap": item.get("market_cap")
                    })
                return normalized

        elif provider == "coinmarketcap":
            url = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/listings/latest"
            headers = {
                "X-CMC_PRO_API_KEY": settings.CMC_API_KEY,
                "Accept": "application/json"
            }
            params = {"convert": "USD", "limit": limit}
            with requests.Session() as session:
                session.headers.update(headers)
                response = session.get(url, params=params)
                response.raise_for_status()
                raw_data = response.json()
                normalized = []
                for item in raw_data["data"]:
                    normalized.append({
                        "name": item["name"],
                        "symbol": item["symbol"],
                        "current_price": item["quote"]["USD"]["price"],
                        "total_volume": item["quote"]["USD"]["volume_24h"],
                        "price_change_percentage_24h": item["quote"]["USD"]["percent_change_24h"],
                        "market_cap": item["quote"]["USD"]["market_cap"]
                    })
                return normalized
        else:
            raise CommandError(f"Неизвестный провайдер: {provider}")
