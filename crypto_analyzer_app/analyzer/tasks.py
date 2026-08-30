from datetime import timedelta

import requests
from celery import shared_task
from django.conf import settings
from django.core.cache import cache
from django.db.models import Sum
from django.utils import timezone

from analyzer.models import Coin, CoinPrice, Snapshot

from .serializer import CoinPriceAnalyticSerializer
from .services import get_market_stats, get_top_movers, get_top_volume


def _fetch_data(provider, limit):
    if provider == "coingecko":
        url = "https://api.coingecko.com/api/v3/coins/markets"
        params = {"vs_currency": "usd", "order": "market_cap_desc", "per_page": limit, "page": 1}

        with requests.Session() as session:
            response = session.get(url, params=params)
            response.raise_for_status()
            raw_data = response.json()
            return raw_data

    elif provider == "coinmarketcap":
        url = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/listings/latest"

        header = {"X-CMC_PRO_API_KEY": settings.CMC_API_KEY, "Accept": "application/json"}

        params = {"convert": "USD", "limit": limit}

        with requests.Session() as session:
            session.headers.update(header)
            response = session.get(url, params=params)
            response.raise_for_status()
            raw_data = response.json()

            normalized = []
            for item in raw_data["data"]:
                normalized.append(
                    {
                        "name": item["name"],
                        "symbol": item["symbol"].lower(),
                        "current_price": item["quote"]["USD"]["price"],
                        "total_volume": item["quote"]["USD"]["volume_24h"],
                        "price_change_percentage_24h": item["quote"]["USD"]["percent_change_24h"],
                    }
                )

            return normalized


@shared_task(bind=True, max_retries=3, retry_backoff=True, retry_backoff_max=300)
def fetch_snapshot_task(self, provider: str = "coingecko", limit: int = 5):
    if provider == "coinmarketcap" and not settings.CMC_API_KEY:
        return {"error": "Отсутствует API ключ"}

    recent = Snapshot.objects.filter(provider=provider, created_at__gte=timezone.now() - timedelta(minutes=5)).first()
    if recent:
        return {"snapshot_id": recent.id, "already_exists": True}

    try:
        coins_data = _fetch_data(provider, limit)
    except requests.exceptions.RequestException as exc:
        raise self.retry(exc=exc)

    snapshot = Snapshot.objects.create(provider=provider, total_coins=len(coins_data), total_market_cap=0)

    for coin_data in coins_data:
        name = coin_data.get("name")
        symbol = coin_data.get("symbol")
        current_price = coin_data.get("current_price", 0)
        volume = coin_data.get("total_volume", 0)
        change = coin_data.get("price_change_percentage_24h", 0)

        coin, created = Coin.objects.get_or_create(symbol=symbol, defaults={"name": name})

        CoinPrice.objects.create(
            coin=coin, snapshot=snapshot, price=current_price or 0, volume_24h=volume or 0, change_24h=change or 0
        )

    total_market_cap = CoinPrice.objects.filter(snapshot=snapshot).aggregate(total=Sum("price"))["total"] or 0
    snapshot.total_market_cap = total_market_cap
    snapshot.save()

    market_stats = get_market_stats()
    top_movers = get_top_movers()
    top_volume = get_top_volume()

    mover_serializer = CoinPriceAnalyticSerializer(top_movers, many=True)
    value_serializer = CoinPriceAnalyticSerializer(top_volume, many=True)

    cache.set("market_stats", market_stats, 4200)
    cache.set("top_movers", mover_serializer.data, 4200)
    cache.set("volume_leaders", value_serializer.data, 4200)

    return {"snapshot_id": snapshot.id, "total_coins": snapshot.total_coins}
