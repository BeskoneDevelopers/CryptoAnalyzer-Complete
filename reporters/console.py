from .base import BaseReporter

from rich.console import Console
from rich.table import Table
from rich.panel import Panel


class ConsoleReporter(BaseReporter):

    def __init__(self, console: Console | None = None):
        super().__init__()
        self.console = console if console is not None else Console()

    def report(self, data: dict) -> None:
        self.console.print(Panel.fit(
            f"[bold cyan] Crypto Market Analysis[/bold cyan]\n"
            f"[dim]Source: {data['provider']}[/dim]\n"
            f"[dim]Generated: {data['generated_at']}[/dim]",
            border_style="cyan"
        ))

        gainers_table = Table(
            title="Top gainers",
            style="green",
            header_style="bold green"
        )
        gainers_table.add_column("Coin", style="cyan")
        gainers_table.add_column("Symbol", style="yellow")
        gainers_table.add_column("Price", justify="right")
        gainers_table.add_column("24H Change", style="green", justify="right")

        for coin in data["top_gainers"]:
            change = coin["24h_change"]
            price = coin["price"]

            change_str = (
                f"{change:+.2f}%"
                if change is not None
                else "Данных нет"
            )
            price_str = (
                f"${price:,.2f}"
                if price is not None
                else "Данных нет"
            )

            gainers_table.add_row(
                coin["name"],
                coin["symbol"],
                price_str,
                change_str
            )

        self.console.print(gainers_table)

        losers_table = Table(
            title="Top losers",
            style="red",
            header_style="bold red"
        )
        losers_table.add_column("Coin", style="cyan")
        losers_table.add_column("Symbol", style="yellow")
        losers_table.add_column("Price", justify="right")
        losers_table.add_column("24H Change", style="red", justify="right")

        for coin in data["top_losers"]:
            change = coin["24h_change"]
            price = coin["price"]

            change_str = (
                f"{change:+.2f}%"
                if change is not None
                else "Данных нет"
            )
            price_str = (
                f"${price:,.2f}"
                if price is not None
                else "Данных нет"
            )

            losers_table.add_row(
                coin["name"],
                coin["symbol"],
                price_str,
                change_str
            )

        self.console.print(losers_table)

        highest_volume = data["highest_volume"]

        if highest_volume:
            self.console.print(Panel(
                f"[bold] Highest Trading Volume[/bold]\n"
                f"Coin: [cyan]{highest_volume['name']}[/cyan] "
                f"([yellow]{highest_volume['symbol']}[/yellow])\n"
                f"Volume: [green]${highest_volume['volume']:,.0f}[/green]",
                border_style="blue"
            ))

        if data["total_market_cap"] is not None:
            self.console.print(Panel(
                f"[bold] Total Market Cap "
                f"(Top {data['total_coins']})[/bold]\n"
                f"[green]{data['total_market_cap']}[/green]",
                border_style="green"
            ))