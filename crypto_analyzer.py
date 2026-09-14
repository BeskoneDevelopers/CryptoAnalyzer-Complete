import typer
from rich.console import Console
from rich.table import Table

from models.portfolio import CryptoPortfolio
from providers import get_provider
from reporters import get_reporter

from settings import settings, StorageType
from storage.json_storage import JsonStorage
from storage.sqlite_storage import SqliteStorage

from datetime import datetime


app = typer.Typer(
    name="Crypto-analyzer",
    help="Анализ рынка крипты"
)


def get_storage():
    if settings.storage == StorageType.JSON:
        return JsonStorage()
    elif settings.storage == StorageType.SQLITE:
        return SqliteStorage()
    else:
        raise ValueError(f"Неизвестное хранилище: {settings.storage}")

def build_report_data(portfolio: CryptoPortfolio, provider_name: str, top_count: int) -> dict:
    gainers = portfolio.get_top_gainers(top_count)
    losers = portfolio.get_top_losers(top_count)
    highest = portfolio.get_highest_volume()

    return {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "provider": provider_name,
        "total_coins": len(portfolio),
        "total_market_cap": portfolio.get_total_market_cap(),

        "top_gainers": [
            {
                "name": coin.name,
                "symbol": coin.symbol,
                "price": coin.current_price,
                "24h_change": coin.price_change_for_24h,
            }
            for coin in gainers
        ],

        "top_losers": [
            {
                "name": coin.name,
                "symbol": coin.symbol,
                "price": coin.current_price,
                "24h_change": coin.price_change_for_24h,
            }
            for coin in losers
        ],

        "all_coins": [
            {
                "name": coin.name,
                "symbol": coin.symbol,
                "price": coin.current_price,
                "volume_24h": coin.total_volume,
                "24h_change": coin.price_change_for_24h,
            }
            for coin in portfolio
        ],

        "highest_volume": {
            "name": highest.name,
            "symbol": highest.symbol,
            "volume": highest.total_volume,
        } if highest else None,
    }

@app.command()
def analyze(
        source: str = typer.Option(
            "coingecko",
            "--source",
            "-s",
            help="Источник данных"
        ),
        output: str = typer.Option(
            "console",
            "--output",
            "-o",
            help="Формат вывода"
        ),
        top: int = typer.Option(
            3,
            "--top",
            "-t",
            help="Количество лидеров"
        ),
        limit: int = typer.Option(
            50,
            "--limit",
            "-l",
            help="Сколько монет загрузить"
        )
):
    console = Console()

    try:
        provider = get_provider(source)
        reporter = get_reporter(output)

        coins = provider.fetch_top_coins(limit=limit)

        console.print(
            f"[green]✓ Загружено {len(coins)} монет "
            f"через {provider.get_name()}[/green]"
        )

        portfolio = CryptoPortfolio(coins)

        data = build_report_data(
            portfolio,
            provider.get_name(),
            top_count=top,
        )

        with get_storage() as storage:
            storage.save(data)

        reporter.report(data)

    except ValueError as e:
        console.print(f"[red] Ошибка!: {e}[/red]")
        raise typer.Exit(code=1)

    except Exception as e:
        console.print(f"[red] Непредвиденная ошибка: {e}[/red]")
        raise typer.Exit(code=1)


@app.command()
def list_cadr():
    console = Console()

    try:
        with get_storage() as storage:
            cadr = storage.list_cadr()
    except NotImplementedError as e:
        console.print(f"[yellow]⚠ {e}[/yellow]")
        return

    if not cadr:
        console.print("[red]Кадров нету[/red]")
        return

    table = Table(title="Снимки рынка")
    table.add_column("ID", style="cyan")
    table.add_column("Дата", style="green")
    table.add_column("Провайдер")
    table.add_column("Монет")
    table.add_column("Капитализация")

    for shot in cadr:
        table.add_row(
            str(shot[0]),
            shot[1],
            shot[2],
            str(shot[3]),
            f"${shot[4]:,.0f}"
        )

    console.print(table)


@app.command()
def compare_cadr(id1: int, id2: int):
    console = Console()

    try:
        with get_storage() as storage:
            rows = storage.compare_cadr(id1, id2)
    except NotImplementedError as e:
        console.print(f"[yellow]⚠ {e}[/yellow]")
        return

    if not rows:
        console.print("[red]Кадров нету[/red]")
        return

    table = Table(title=f"Сравнение снимков {id1} -> {id2}")
    table.add_column("Монета")
    table.add_column("Старая цена")
    table.add_column("Новая цена")
    table.add_column("Разница")

    for row in rows:
        symbol = row[0]
        old_price = row[1]
        new_price = row[2]
        diff = row[3]

        diff_str = (
            f"[green]+${diff:,.2f}[/green]"
            if diff > 0
            else f"[red]-${abs(diff):,.2f}[/red]"
        )

        table.add_row(
            symbol,
            f"${old_price:,.2f}",
            f"${new_price:,.2f}",
            diff_str
        )

    console.print(table)


if __name__ == "__main__":
    app()