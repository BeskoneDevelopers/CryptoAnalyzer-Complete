from  dataclasses import dataclass #---- Для автоматической генерациии иниицализации

from  typing import Optional

@dataclass
class Coin:

    name: str
    symbol: str
    current_price: Optional[float] = None
    total_volume: Optional[float] = None
    market_cap: Optional[float] = None
    price_change_for_24h: Optional[float] = None

    def __repr__(self):
        chang_str = (f"{self.price_change_for_24h:+.2f}%" if self.price_change_for_24h is not None else "Данные отсутствуют")
        return f"Coin({self.symbol}: {chang_str})"

    def __str__(self) -> str:
        line = f"{self.name}|'{self.symbol}' -- "

        if self.current_price:
            line += f"Price: ${self.current_price:,.2f}"
        else:
            line += "Price: Данные отсутствуют"

        if self.price_change_for_24h:
            line += f" | 24H: {self.price_change_for_24h:+.2f}%"
        else:
            line += " | 24H: Данные отсутствуют"
        return line

    def _compare_change(self, other: "Coin"):
        if not isinstance(other, Coin):
            return NotImplemented
        self_change = self.price_change_for_24h or 0
        other_change = other.price_change_for_24h or 0
        return self_change, other_change



    def __lt__(self, other: "Coin"): # - lt сравнивает - "<"
        se, ot = self._compare_change(other)
        return se < ot if isinstance(se, float) else NotImplemented

    def __gt__(self, other): # - gt сравнивает ">"
        se, ot = self._compare_change(other)
        return se > ot if isinstance(se, float) else NotImplemented

    def __post_init__(self):
        if self.current_price is not None and self.current_price < 0:
            raise ValueError(f"Price cannot be negative: {self.current_price}")

    def compare_by_market_cap(self, other: "Coin"): # аналог lt но сравниваем рыночную капитализвцию
        if not isinstance(other, Coin):
            return NotImplemented

        self_change = self.market_cap or 0
        other_change = other.market_cap or 0

        return self_change < other_change


    @classmethod
    def from_dict(cls, data: dict, source: str = "coingecko") -> "Coin":
        if source == "coingecko":
            return cls(
            name = data.get("name", "None"),
            symbol = data.get("symbol", "None"),
            current_price = data.get("current_price", None),
            total_volume = data.get("total_volume", None),
            market_cap = data.get("market_cap", None),
            price_change_for_24h = data.get("price_change_percentage_24h", None)
            )

        elif source == "coinmarketcap":
            return cls(
                name=data.get("name", "None"),
                symbol=data.get("symbol", "None"),
                current_price=data.get("quote", {}).get("USD", {}).get("price"),
                total_volume=data.get("quote", {}).get("USD", {}).get("volume_24h"),
                market_cap=data.get("quote", {}).get("USD", {}).get("market_cap"),
                price_change_for_24h=data.get("quote", {}).get("USD", {}).get("percent_change_24h")
            )
        else:
            raise ValueError(f"Неизвестный источник - {source}")



