from django.conf import settings

import requests

from analyzer.models import Coin, WatchlistItem


def get_provider():
    if settings.EXCHANGE_PROVIDER == "coingecko":
        return validate_symbol_coingecko

    elif settings.EXCHANGE_PROVIDER == "coinmarketcap":
        return validate_symbol_coinmarketcap

    raise ValueError(
        f"Неизвестный провайдер: {settings.EXCHANGE_PROVIDER}"
    )


def validate_symbol_coingecko(symbol):
    search_symbol = (
        f"https://api.coingecko.com/api/v3/search?query={symbol}"
    )

    with requests.Session() as session:
        response = session.get(search_symbol)
        response.raise_for_status()
        data = response.json()

    for coin in data.get("coins", []):
        if coin.get("symbol", "").lower() == symbol.lower():
            return {
                "valid": True,
                "name": coin.get("name")
            }

    return False


def validate_symbol_coinmarketcap(symbol):
    url = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/map"

    headers = {
        "X-CMC_PRO_API_KEY": settings.CMC_API_KEY,
        "Accept": "application/json",
    }

    params = {
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
                "name": coin.get("name")
            }

    return False


def validate_symbol(symbol):
    provider = get_provider()
    return provider(symbol)


def add_to_watchlist(user, symbol):
    if not symbol:
        return {"error": f"{symbol} не передан"}

    valid = validate_symbol(symbol)

    if not valid:
        return {"error": f"Монета с символом - {symbol} не найдена"}

    coin, _ = Coin.objects.get_or_create(
        symbol=symbol,
        defaults={"name": valid.get("name")}
    )

    watchlist, _ = WatchlistItem.objects.get_or_create(
        user=user,
        coin=coin,
    )

    return watchlist


def remove_from_watchlist(user, symbol):
    if not symbol or not user:
        return {"error": "Передана неполная информация"}

    delete, _ = WatchlistItem.objects.filter(
        user=user,
        coin__symbol=symbol,
    ).delete()

    if delete:
        return {
            "valid": True,
            "message": "Данные успешно удалены"
        }

    return {
        "valid": False,
        "message": "Данные не найдены"
    }


def get_watchlist(user):
    if not user:
        return {"error": f"Пользователь {user} не найден"}

    return WatchlistItem.objects.filter(
        user=user
    ).select_related("coin")
