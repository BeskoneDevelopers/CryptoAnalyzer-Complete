from django.conf import settings

from analyzer.models import Coin, Snapshot, CoinPrice, WatchlistItem

def get_provider():
    if settings.EXCHANGE_PROVIDER == "coingecko":
        return coingecko_fetch_function
    elif settings.EXCHANGE_PROVIDER == "coinmarketcap":
        return coinmarketcap_fetch_function

def validate_symbol(symbol):
    search_symbol = f"https://api.coingecko.com/api/v3/search?query={symbol}"

    with requests.Session() as session:
        response = session.get(search_symbol)
        response.raise_for_status()
        data = response.json()

        for coin in data.get("coins", []):
            if coin.get("symbol", "").lower() == symbol.lower():
                return {"valid": True, "name": coin.get("name")}
        return False



def add_to_watchlist(user, symbol):

    if not symbol:
        return {"error": f"{symbol} не передан"}

    valid = validate_symbol(symbol)
    if valid:
        coin, created = Coin.objects.get_or_create(
            symbol=symbol,
            defaults={"name": valid.get("name")}
        )
        watchlist, created = WatchlistItem.objects.get_or_create(
            user=user,
            coin=coin,
        )
        return watchlist
    else:
        return {"error": f"Монета с символом - {symbol} не найдена"}

def remove_from_watchlist(user, symbol):
    if not symbol or not user:
        return {"error": "Передана неполная информация"}

    delete, _ = WatchlistItem.objects.filter(
        user=user,
        coin__symbol=symbol,
    ).delete()

    if delete:
        return {"valid": True, "message": "Данные успешно удалены"}
    return {"valid": False, "message": "Данные не найдены"}

def get_watchlist(user):
    if not user:
        return {"error": f"Пользователь {user} не найден"}

    return WatchlistItem.objects.filter(user=user).select_related("coin")

