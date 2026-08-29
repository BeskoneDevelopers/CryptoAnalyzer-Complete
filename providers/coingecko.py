import time
from functools import wraps
from typing import List

import requests

from models.coin import Coin
from .base import BaseProvider

def retry(attempts: int = 3, delay: float = 1):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(attempts):
                try:
                    return func(*args, **kwargs)
                except ConnectionError:
                    if attempt == attempts - 1:
                        raise
                    time.sleep(delay)

        return wrapper

    return decorator


class CoinGeckoProvider(BaseProvider):

    URL_API = "https://api.coingecko.com/api/v3/coins/markets"
    def __init__(self, time_out: int = 10):
        self.time_out = time_out

    @retry(attempts=3, delay=1)
    def fetch_top_coins(self, limit: int = 50) -> List[Coin]:
        params = {
            "vs_currency": "usd",
            "order": "market_cap_desc",
            "per_page": limit,
            "page": 1
        }
        with requests.Session() as session:
            response = session.get(self.URL_API, params=params, timeout=self.time_out)
            response.raise_for_status()
            raw_data = response.json()
            data = [Coin.from_dict(item, source="coingecko") for item in raw_data]
            return data


    def get_name(self) -> str:
        return "CoinGecko"