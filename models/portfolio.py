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

    def __getitem__(self, symbol: str):
        for coin in self._coin:
            if coin.symbol == symbol:
                return coin
        raise KeyError(f"Монета {symbol} не найдена")

    def get_top_gainers(self, count: int = 3):
        return sorted(self._coin, key=lambda c: c.price_change_for_24h if c.price_change_for_24h is not None else float("-inf"), reverse=True)[:count]

    def get_top_losers(self, count: int = 3):
        valid_coins = [coin for coin in self._coin if coin.price_change_for_24h is not None]
        return sorted(valid_coins, key=lambda c: c.price_change_for_24h)[:count]

    def get_highest_volume(self):
        if not self._coin:
            return None
        return max(self._coin, key=lambda coins: coins.total_volume or 0)

    def get_total_market_cap(self):
        return sum(coin.market_cap or 0 for coin in self._coin)

    def __iter__(self):
        return iter(self._coin)
