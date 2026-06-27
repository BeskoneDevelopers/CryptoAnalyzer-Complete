import functools
import time

import requests
import json

from rich.console import Console
from datetime import datetime

from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn


#Декоратор "retry" - Максимум попыток - 3, время ожидания - +-2сек ()
def retry(max_attempt: int = 3, expectation: int = 2):
    def decor(func):
        @functools.wraps(func)
        def wraps(*args, **kwargs):
            rtry = 0

            while rtry < max_attempt:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    rtry += 1

                    if rtry < max_attempt:
                        print(f"Попытка номер - {rtry} не удалась. Ошибка - {e}")
                        time.sleep(expectation)

            raise Exception("Ошибка. Все попытки исчерпаны")
        return wraps
    return decor


#Основной код. *Стоит изучить Rich.*
class Analyzer:
    def __init__(self):
        self.console = Console()
        self.result = {}
        self.data = None

    API_URL = "https://api.coingecko.com/api/v3/coins/markets"

    @retry(max_attempt=3, expectation=2)
    def featch_market(self, vs_currency: str = "usd", order: str = "market_cap_desc", per_page: int = 50, page: int = 1):
        params = {
            "vs_currency": vs_currency,
            "order": order,
            "per_page": per_page,
            "page": page
        }
        response = requests.get(self.API_URL, params=params, timeout=10)

        return response.json()


    def analyze_data(self):

        sorted_change = sorted(self.data, key=lambda x: x.get("price_change_percentage_24h", 0) or 0, reverse=True) #Подсказал ИИ агент

        top_coin = sorted_change[:3] #Даст первые 3 коина

        down_coin = sorted_change[-3:] #Даст последние 3 коина
        down_coin.reverse() #Покажет мне самые донные валюты начиная с последней

        highest_volume = max(self.data, key=lambda x: x.get("total_volume", 0) or 0) #Подсказал ИИ агент

        total_cap = sum(coin.get('market_cap', 0) or 0 for coin in self.data)

        self.result = {
            "generate_AT": datetime.now(),
            "total_coins": len(self.data),
            "total_market_cap": total_cap,
            "top_coin": [
                {
                    "name": coin["name"],
                    "symbol": coin["symbol"],
                    "change_24h": coin.get("price_change_percentage_24h", 0)
                } for coin in top_coin
            ],
            "top_down_coin": [
                {
                    "name": coin["name"],
                    "symbol": coin["symbol"],
                    "change_24h": coin.get("price_change_percentage_24h", 0)
                } for coin in down_coin
            ],
            "highest_volume": {
                    "name": highest_volume["name"],
                    "symbol": highest_volume["symbol"],
                    "volume": highest_volume.get("total_volume", 0)
                }
        }

        return self.result


