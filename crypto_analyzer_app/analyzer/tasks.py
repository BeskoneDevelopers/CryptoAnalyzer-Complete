from datetime import timedelta

import requests
from celery import shared_task
from django.conf import settings
from django.db.models import Sum
from django.utils import timezone

from analyzer.models import Coin, CoinPrice, Snapshot
from analyzer.services import refresh_analytics_cache


def _fetch_data(provider, limit):
    if provider == "coingecko":
        return _fetch_coingecko(limit)

    elif provider == "coinmarketcap":
        return _fetch_coinmarketcap(limit)

    else:
        raise ValueError("Неизвестный провайдер")


def _fetch_coingecko(limit: int):
    url = "https://api.coingecko.com/api/v3/coins/markets"

    params: dict[str, str | int] = {
        "vs_currency": "usd",
        "order": "market_cap_desc",
        "per_page": limit,
        "page": 1,
    }

    with requests.Session() as session:
        response = session.get(url, params=params)
        response.raise_for_status()
        raw_data = response.json()
        return raw_data


def _fetch_coinmarketcap(limit: int):
    url = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/listings/latest"

    api_key = settings.CMC_API_KEY

    if not api_key:
        raise ValueError("Отсутствует API ключ CoinMarketCap")

    header: dict[str, str] = {
        "X-CMC_PRO_API_KEY": api_key,
        "Accept": "application/json",
    }

    params: dict[str, str | int] = {
        "convert": "USD",
        "limit": limit,
    }

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
                    "market_cap": item["quote"]["USD"]["market_cap"],
                }
            )

        return normalized


def _get_retry_countdown(retries: int) -> int:
    return min(60 * (2**retries), 300)


@shared_task(bind=True, max_retries=3)
def fetch_snapshot_task(self, provider: str = "coingecko", limit: int = 5):
    if provider == "coinmarketcap" and not settings.CMC_API_KEY:
        return {"error": "Отсутствует API ключ"}

    recent = Snapshot.objects.filter(provider=provider, created_at__gte=timezone.now() - timedelta(minutes=3)).first()
    if recent:
        return {"snapshot_id": recent.pk, "already_exists": True}

    try:
        coins_data = _fetch_data(provider, limit)
    except (
        requests.exceptions.ConnectionError,
        requests.exceptions.Timeout,
    ) as exc:
        countdown = _get_retry_countdown(self.request.retries)
        raise self.retry(exc=exc, countdown=countdown)

    snapshot = Snapshot.objects.create(provider=provider, total_coins=len(coins_data), total_market_cap=0)

    for coin_data in coins_data:
        name = coin_data.get("name")
        symbol = coin_data.get("symbol")
        current_price = coin_data.get("current_price")
        volume = coin_data.get("total_volume")
        change = coin_data.get("price_change_percentage_24h")
        market_cap = coin_data.get("market_cap")

        coin, _ = Coin.objects.get_or_create(
            symbol=symbol,
            defaults={"name": name},
        )

        CoinPrice.objects.create(
            coin=coin,
            snapshot=snapshot,
            price=current_price,
            volume_24h=volume,
            change_24h=change,
            market_cap=market_cap,
        )

    total_market_cap = CoinPrice.objects.filter(snapshot=snapshot).aggregate(total=Sum("market_cap"))["total"] or 0

    snapshot.total_market_cap = total_market_cap
    snapshot.save()

    refresh_analytics_cache()

    return {
        "snapshot_id": snapshot.pk,
        "total_coins": snapshot.total_coins,
    }
