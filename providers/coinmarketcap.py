import os

import requests
from dotenv import load_dotenv
from .base import BaseProvider
from models.coin import Coin

from typing import List

class CoinMarketCapProvider(BaseProvider):
    URL_API = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/listings/latest"

    def __init__(self, api_key: str = None, time_out: int = 10):
        load_dotenv()
        self.api_key = api_key or os.getenv("API_KEY")

        if not self.api_key:
            raise ValueError("ключ не найден")

        self.time_out = time_out

    def featch_top_coins(self, limit: int = 50) -> List[Coin]:
        headers = {
            "X-CMC_PRO_API_KEY": self.api_key,
            "Accept": "application/json"
        }

        params = {
            "convert": "USD",
            "limit": limit
        }

        with requests.Session() as session:
            session.headers.update(headers)
            response = session.get(self.URL_API, params=params)
            response.raise_for_status()
            raw_data = response.json()
            data = [Coin.from_dict(item, source="coinmarketcap") for item in raw_data["data"]]
            return data



    def get_name(self) -> str:
        return "CoinMarketCap"
