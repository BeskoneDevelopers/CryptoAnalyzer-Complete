from .base import BaseProvider
from .coingecko import CoinGeckoProvider
from .coinmarketcap import CoinMarketCapProvider

def get_provider(source: str) -> BaseProvider:
    if source == "coingecko":
        return CoinGeckoProvider()
    elif source == "coinmarketcap":
        return CoinMarketCapProvider()
    else:
        raise ValueError("Выберите из списка: 'coingecko' | 'coinmarketcap'")
