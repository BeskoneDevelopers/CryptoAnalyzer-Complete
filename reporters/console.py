from models.portfolio import CryptoPortfolio
from .base import BaseReporter

from rich.console import Console
from rich.table import Table
from rich.panel import Panel




class ConsoleReporter(BaseReporter):
    def __init__(self):
        super().__init__()
        self.console = Console()

    def report(self, portfolio: CryptoPortfolio, provider_name: str, top_count: int = 3) -> None:
        self.console.print(Panel.fit(
            f"[bold cyan]📊 Crypto Market Analysis[/bold cyan]\n"
            f"[dim]Source: {provider_name}[/dim]\n"
            f"[dim]Generated: {self.generate_at}[/dim]",
            border_style="cyan"
        ))

        gainers = portfolio.get_top_gainers(top_count)
        losers = portfolio.get_top_losers(top_count)
        highest_volume = portfolio.get_highest_volume()
        total_cap = portfolio.get_total_market_cap()

        gainers_table = Table(
            title="Top gainers",
            style="green",
            header_style="bold green"
        )
        gainers_table.add_column("Coin", style="cyan")
        gainers_table.add_column("Symbol", style="yellow")
        gainers_table.add_column("Price", justify="right")
        gainers_table.add_column("24H Change", style="green", justify="right")

        for coin in gainers:
            change_str = f"+{coin.price_change_for_24h:.2f}%" if coin.price_change_for_24h else "Данных нет"
            price_str = f"${coin.current_price:,.2f}" if coin.current_price else "Данных нет"

            gainers_table.add_row(
                coin.name,
                coin.symbol,
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

        for coin in losers:
            change_str = f"{coin.price_change_for_24h:.2f}%" if coin.price_change_for_24h else "Данных нет"
            price_str = f"${coin.current_price:,.2f}" if coin.current_price else "Данных нет"

            losers_table.add_row(
                coin.name,
                coin.symbol,
                price_str,
                change_str
            )
        self.console.print(losers_table)

        if highest_volume:
            self.console.print(Panel(
                f"[bold]💰 Highest Trading Volume[/bold]\n"
                f"Coin: [cyan]{highest_volume.name}[/cyan] ([yellow]{highest_volume.symbol}[/yellow])\n"
                f"Volume: [green]${highest_volume.total_volume:,.0f}[/green]",
                border_style="blue"
            ))

        if total_cap:
            self.console.print(Panel(
                f"[bold]📈 Total Market Cap (Top {len(portfolio)})[/bold]\n"
                f"[green]{total_cap}[/green]",
                border_style="green"
            ))