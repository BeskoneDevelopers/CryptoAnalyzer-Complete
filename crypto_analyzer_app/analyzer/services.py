from collections.abc import Callable, Iterable
from decimal import Decimal
from typing import Any

import requests
from django.conf import settings
from django.contrib.auth.models import User
from django.core.cache import cache
from django.db.models import Avg, Max, Min, QuerySet

from .models import Coin, CoinPrice, Snapshot, WatchlistItem

ANALYTICS_CACHE_TTL = 4200
MARKET_STATS_CACHE_KEY = "market_stats"
TOP_MOVERS_CACHE_KEY = "top_movers"
VOLUME_LEADERS_CACHE_KEY = "volume_leaders"


def get_provider() -> Callable[[str], dict[str, Any] | bool]:
    if settings.EXCHANGE_PROVIDER == "coingecko":
        return validate_symbol_coingecko

    elif settings.EXCHANGE_PROVIDER == "coinmarketcap":
        return validate_symbol_coinmarketcap

    raise ValueError(f"Неизвестный провайдер: {settings.EXCHANGE_PROVIDER}")


def validate_symbol_coingecko(symbol: str) -> dict[str, Any] | bool:
    search_symbol = f"https://api.coingecko.com/api/v3/search?query={symbol}"

    with requests.Session() as session:
        response = session.get(search_symbol)
        response.raise_for_status()
        data = response.json()

    for coin in data.get("coins", []):
        if coin.get("symbol", "").lower() == symbol.lower():
            return {"valid": True, "name": coin.get("name")}

    return False


def validate_symbol_coinmarketcap(symbol: str) -> dict[str, Any] | bool:
    api_key = settings.CMC_API_KEY
    if not api_key:
        raise ValueError("Отсутствует API ключ CoinMarketCap")
    url = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/map"
    headers: dict[str, str] = {
        "X-CMC_PRO_API_KEY": api_key,
        "Accept": "application/json",
    }
    params: dict[str, str] = {
        "symbol": symbol.upper(),
    }
    with requests.Session() as session:
        session.headers.update(headers)
        response = session.get(url, params=params)
        response.raise_for_status()
        data = response.json()

    for coin in data.get("data", []):
        if coin.get("symbol", "").lower() == symbol.lower():
            return {
                "valid": True,
                "name": coin.get("name"),
            }

    return False


def validate_symbol(symbol: str) -> dict[str, Any] | bool:
    provider = get_provider()
    return provider(symbol)


def add_to_watchlist(
    user: User,
    symbol: str,
    coin_data: dict[str, Any],
) -> WatchlistItem:
    symbol = symbol.strip().upper()

    coin, _ = Coin.objects.get_or_create(
        symbol=symbol,
        defaults={"name": coin_data["name"]},
    )

    watchlist, _ = WatchlistItem.objects.get_or_create(
        user=user,
        coin=coin,
    )

    return watchlist


def remove_from_watchlist(user: User, symbol: str) -> dict[str, Any]:
    symbol = symbol.strip().upper()

    deleted, _ = WatchlistItem.objects.filter(
        user=user,
        coin__symbol=symbol,
    ).delete()

    if deleted:
        return {
            "valid": True,
            "message": "Данные успешно удалены",
        }

    return {
        "valid": False,
        "message": "Данные не найдены",
    }


def get_watchlist(user: User) -> dict[str, str] | QuerySet[WatchlistItem]:
    if not user:
        return {"error": f"Пользователь {user} не найден"}

    return WatchlistItem.objects.filter(
        user=user,
    ).select_related("coin")


def get_market_stats() -> dict[str, Any]:
    last = Snapshot.objects.last()
    if not last:
        return {"error": "Снимков нет!"}

    status = CoinPrice.objects.filter(snapshot=last).aggregate(
        min_price=Min("price"),
        max_price=Max("price"),
        avg_price=Avg("price"),
    )
    return {
        "snapshot_id": last.pk,
        "provider": last.provider,
        "total_market_cap": last.total_market_cap,
        **status,
    }


def get_toper(sort_field: str, limit: int = 10) -> dict[str, str] | QuerySet[CoinPrice]:
    sort_fields = {
        "change": "-change_24h",
        "volume": "-volume_24h",
    }

    filt = sort_fields.get(sort_field)
    if not filt:
        raise ValueError("Неверное поле сортировки")

    last = Snapshot.objects.last()
    if not last:
        return {"error": "Снимков нет!"}

    return CoinPrice.objects.filter(snapshot=last).select_related("coin").order_by(filt)[:limit]


def get_top_movers(limit: int = 10) -> dict[str, str] | QuerySet[CoinPrice]:
    return get_toper("change", limit)


def get_top_volume(limit: int = 10) -> dict[str, str] | QuerySet[CoinPrice]:
    return get_toper("volume", limit)


def get_latest_price(coin: Coin) -> Decimal:
    latest_snapshot = Snapshot.objects.order_by("-created_at").first()

    if latest_snapshot is None:
        raise ValueError("Снимок рынка не найден")

    try:
        coin_price = CoinPrice.objects.get(
            snapshot=latest_snapshot,
            coin=coin,
        )
    except CoinPrice.DoesNotExist:
        raise ValueError("Цена монеты не найдена") from None

    if coin_price.price is None:
        raise ValueError("Цена монеты не найдена")

    return coin_price.price


def get_latest_prices(coin_ids: Iterable[int]) -> dict[int, Decimal]:
    latest_snapshot = Snapshot.objects.order_by("-created_at").first()

    if latest_snapshot is None:
        raise ValueError("Снимок рынка не найден")

    prices = CoinPrice.objects.filter(
        snapshot=latest_snapshot,
        coin_id__in=coin_ids,
    )
    return {price.coin_id: price.price for price in prices if price.price is not None}


def get_or_set_cache(
    cache_key: str,
    loader: Callable[[], Any],
    *,
    force_refresh: bool = False,
) -> Any:
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
    return get_or_set_cache(
        MARKET_STATS_CACHE_KEY,
        get_market_stats,
        force_refresh=force_refresh,
    )


def get_serialized_top_movers() -> Any:
    from .serializer import CoinPriceAnalyticSerializer

    movers = get_top_movers()

    if isinstance(movers, dict) and "error" in movers:
        return movers

    serializer = CoinPriceAnalyticSerializer(movers, many=True)
    return serializer.data


def get_serialized_top_volume() -> Any:
    from .serializer import CoinPriceAnalyticSerializer

    volume = get_top_volume()

    if isinstance(volume, dict) and "error" in volume:
        return volume

    serializer = CoinPriceAnalyticSerializer(volume, many=True)
    return serializer.data


def get_cached_top_movers(force_refresh: bool = False) -> Any:
    return get_or_set_cache(
        TOP_MOVERS_CACHE_KEY,
        get_serialized_top_movers,
        force_refresh=force_refresh,
    )


def get_cached_top_volume(force_refresh: bool = False) -> Any:
    return get_or_set_cache(
        VOLUME_LEADERS_CACHE_KEY,
        get_serialized_top_volume,
        force_refresh=force_refresh,
    )


def refresh_analytics_cache() -> None:
    get_cached_market_stats(force_refresh=True)
    get_cached_top_movers(force_refresh=True)
    get_cached_top_volume(force_refresh=True)
