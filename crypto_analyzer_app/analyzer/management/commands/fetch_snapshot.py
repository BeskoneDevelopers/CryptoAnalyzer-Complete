from django.core.management.base import BaseCommand
from analyzer.models import Coin, Snapshot, CoinPrice
from django.db.models import Sum
from django.conf import settings

import requests

class Command(BaseCommand):
    help = "Извлекает крипто-данные и создает снимок"

    def add_arguments(self, parser):
        parser.add_argument("--provider", type=str, default="coingecko")
        parser.add_argument("--limit", type=int, default=100)

    def handle(self, *args, **options):
        provider = options["provider"]
        limit = options["limit"]

        if provider == "coinmarketcap" and not settings.CMC_API_KEY:
            self.stderr.write("Отсутствует API ключ в файле .env")
            return

        coins_data = self.fetch_data(provider,limit)


        snapshot = Snapshot.objects.create(
            provider=provider,
            total_coins=len(coins_data),
            total_market_cap=0
        )


        for coin_data in coins_data:
            name = coin_data.get("name")
            symbol = coin_data.get("symbol")
            current_price = coin_data.get('current_price', 0)
            volume = coin_data.get('total_volume', 0)
            change = coin_data.get('price_change_percentage_24h', 0)

            coin, created = Coin.objects.get_or_create(
                symbol=symbol,
                defaults={"name": name}
            )

            CoinPrice.objects.create(
                coin=coin,
                snapshot=snapshot,
                price=current_price or 0,
                volume_24h=volume or 0,
                change_24h=change or 0
            )

        total_market_cap = CoinPrice.objects.filter(snapshot=snapshot).aggregate(
            total=Sum('price')) ['total'] or 0
        snapshot.total_market_cap = total_market_cap
        snapshot.save()


        self.stdout.write(f"Создание snapshot - {snapshot.id}")

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
                return raw_data

        elif provider == "coinmarketcap":
            url = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/listings/latest"

            header = {
                "X-CMC_PRO_API_KEY": settings.CMC_API_KEY,
                "Accept": "application/json"
            }

            params = {
                "convert": "USD",
                "limit": limit
            }

            with requests.Session() as session:
                session.headers.update(header)
                response = session.get(url, params=params)
                response.raise_for_status()
                raw_data = response.json()

                normalized = []
                for item in raw_data["data"]:
                    normalized.append({
                        "name": item["name"],
                        "symbol": item["symbol"].lower(),
                        "current_price": item["quote"]["USD"]["price"],
                        "total_volume": item["quote"]["USD"]["volume_24h"],
                        "price_change_percentage_24h": item["quote"]["USD"]["percent_change_24h"]
                    })

                return normalized

        else:
            self.stderr.write(f"Неизвестный провайдер - {provider}")
            return []

