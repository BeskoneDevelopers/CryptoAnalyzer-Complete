from collections.abc import Callable
from typing import Any

import requests
from django.contrib.auth.models import User
from django.core.cache import cache
from django.db.models import Avg, Max, Min, QuerySet

from analyzer.models import Coin, CoinPrice, Snapshot, WatchlistItem

ANALYTICS_CACHE_TTL = 4200

MARKET_STATS_CACHE_KEY = "market_stats"
TOP_MOVERS_CACHE_KEY = "top_movers"
VOLUME_LEADERS_CACHE_KEY = "volume_leaders"


def validate_symbol(symbol: str) -> dict[str, Any] | bool:
    search_symbol = f"https://api.coingecko.com/api/v3/search?query={symbol}"

    with requests.Session() as session:
        response = session.get(search_symbol)
        response.raise_for_status()
        data = response.json()

        for coin in data.get("coins", []):
            if coin.get("symbol", "").lower() == symbol.lower():
                return {"valid": True, "name": coin.get("name")}
        return False


def add_to_watchlist(user: User, symbol: str) -> dict[str, str] | WatchlistItem:
    if not symbol:
        return {"error": f"{symbol} не передан"}

    valid = validate_symbol(symbol)
    if valid and isinstance(valid, dict):
        coin, created = Coin.objects.get_or_create(symbol=symbol, defaults={"name": valid.get("name")})
        watchlist, created = WatchlistItem.objects.get_or_create(
            user=user,
            coin=coin,
        )
        return watchlist
    else:
        return {"error": f"Монета с символом - {symbol} не найдена"}


def remove_from_watchlist(user: User, symbol: str) -> dict[str, Any]:
    if not symbol or not user:
        return {"error": "Передана неполная информация"}

    delete, _ = WatchlistItem.objects.filter(
        user=user,
        coin__symbol=symbol,
    ).delete()

    if delete:
        return {"valid": True, "message": "Данные успешно удалены"}
    return {"valid": False, "message": "Данные не найдены"}


def get_watchlist(user: User) -> dict[str, str] | QuerySet[WatchlistItem]:
    if not user:
        return {"error": f"Пользователь {user} не найден"}

    return WatchlistItem.objects.filter(user=user).select_related("coin")


def get_market_stats() -> dict[str, Any]:
    last: Snapshot | None = Snapshot.objects.last()
    if not last:
        return {"error": "Снимков нет!"}

    status = CoinPrice.objects.filter(snapshot=last).aggregate(min_price=Min("price"), max_price=Max("price"), avg_price=Avg("price"))

    return {"snapshot_id": last.pk, "provider": last.provider, "total_market_cap": last.total_market_cap, **status}


def get_top_movers(limit: int = 10) -> dict[str, str] | QuerySet[CoinPrice]:
    last = Snapshot.objects.last()
    if not last:
        return {"error": "Снимков нет!"}

    status = CoinPrice.objects.filter(snapshot=last).select_related("coin").order_by("-change_24h")[:limit]

    return status


def get_top_volume(limit: int = 10) -> dict[str, str] | QuerySet[CoinPrice]:
    last = Snapshot.objects.last()
    if not last:
        return {"error": "Снимков нет!"}

    status = CoinPrice.objects.filter(snapshot=last).select_related("coin").order_by("-volume_24h")[:limit]

    return status


def get_or_set_cache(cache_key: str, loader: Callable[[], Any], *, force_refresh: bool = False) -> Any:
    if not force_refresh:
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

    data = loader()

    if isinstance(data, dict) and "error" in data:
        return data

    cache.set(cache_key, data, ANALYTICS_CACHE_TTL)
    return data


def get_cached_market_stats(force_refresh: bool = False) -> dict[str, Any]:
    return get_or_set_cache(MARKET_STATS_CACHE_KEY, get_market_stats, force_refresh=force_refresh)


def get_serialized_top_movers() -> Any:
    from analyzer.serializer import CoinPriceAnalyticSerializer

    movers = get_top_movers()

    if isinstance(movers, dict) and "error" in movers:
        return movers

    serialized = CoinPriceAnalyticSerializer(movers, many=True)
    return serialized.data


def get_serialized_top_volume() -> Any:
    from analyzer.serializer import CoinPriceAnalyticSerializer

    volume = get_top_volume()

    if isinstance(volume, dict) and "error" in volume:
        return volume

    serialized = CoinPriceAnalyticSerializer(volume, many=True)
    return serialized.data


def get_cached_top_movers(force_refresh: bool = False) -> Any:
    return get_or_set_cache(TOP_MOVERS_CACHE_KEY, get_serialized_top_movers, force_refresh=force_refresh)


def get_cached_top_volume(force_refresh: bool = False) -> Any:
    return get_or_set_cache(VOLUME_LEADERS_CACHE_KEY, get_serialized_top_volume, force_refresh=force_refresh)


def refresh_analytics_cache() -> None:
    get_cached_market_stats(force_refresh=True)
    get_cached_top_movers(force_refresh=True)
    get_cached_top_volume(force_refresh=True)
