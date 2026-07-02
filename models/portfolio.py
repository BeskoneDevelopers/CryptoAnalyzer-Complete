from typing import List, Optional

from .coin import Coin

class CryptoPortfolio:
    def __init__(self, coins: Optional[List[Coin]] = None):
        self._coin = coins or []

    def add_coin(self, coin: Coin):
        self._coin.append(coin)

    def add_coins(self, coin: List[Coin]):
        self._coin.extend(coin)

    @property
    def coins(self):
        return self._coin.copy()

    def __len__(self):
        return len(self._coin)

    def get_top_gainers(self, count: int = 3):
        return sorted(self._coin, key=lambda coins: coins.price_change_for_24h or float("-inf"), reverse=True)[:count]

    def get_top_losers(self, count: int = 3):
        return sorted(self._coin, key=lambda coins: coins.price_change_for_24h or float("-inf"))[:count]

    def get_highest_volume(self):
        return max(self._coin, key=lambda coins: coins.total_volume or 0)

    def get_total_market_cap(self):
        return sum(coin.market_cap or 0 for coin in self._coin)

    def __iter__(self):
        return iter(self._coin)
