import requests

from typing import List
from .base import BaseProvider
from models.coin import Coin




class CoinGeckoProvider(BaseProvider):

    URL_API = "https://api.coingecko.com/api/v3/coins/markets"
    def __init__(self, time_out: int = 10):
        self.time_out = time_out

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