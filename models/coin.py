from  dataclasses import dataclass #---- Для автоматической генерациии иниицализации

from  typing import Optional

@dataclass
class Coin:

    name: str
    symbol: str
    current_price: Optional[float] = None
    total_value: Optional[float] = None
    market_cap: Optional[float] = None
    price_change_for_24h: Optional[float] = None

    def __repr__(self):
        chang_str = (f"{self.price_change_for_24h:+.2f}%" if self.price_change_for_24h is not None else "Данные отсутствуют")
        return f"Coin({self.symbol}: {chang_str}"

    def __str__(self) -> str:
        line = f"{self.name}|'{self.symbol}' -- "

        if self.current_price:
            line += f"Price: ${self.current_price:,.2f}" if self.current_price
        else:
            line += "Price: Данные отсутствуют"

        if self.price_change_for_24h:
            line += f" | 24H: {self.price_change_for_24h:+.2f}%"
        else:
            line += " | 24H: Данные отсутствуют"
        return line

    def __lt__(self, other: "Coin"): # - lt сравнивает - "<"
        if not isinstance(other, Coin):
            return NotImplemented

        self_change = self.price_change_for_24h or 0
        other_change = other.price_change_for_24h or 0

        return self_change < other_change

    def __gt__(self, other): # - gt сравнивает ">"
        if not isinstance(other, Coin):
            return NotImplemented

        self_change = self.price_change_for_24h or 0
        other_change = other.price_change_for_24h or 0

        return self_change > other_change
