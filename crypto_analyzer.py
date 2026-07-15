import typer
from rich.console import Console
from rich.table import Table


from models.portfolio import CryptoPortfolio
from providers import get_provider
from reporters import get_reporter


from settings import settings, StorageType
from storage.json_storage import JsonStorage
from storage.sqlite_storage import SqliteStorage

app = typer.Typer(
    name="Crypto-analyzer",
    help="Анализ рынка крипты"
)

@app.command()
def analyze(
        source: str = typer.Option("coingecko", "--source", "-s", help="Источник данных"),
        output: str = typer.Option("console", "--output", "-o", help="Формат вывода"),
        top: int = typer.Option(3, "--top", "-t", help="Количество лидеров"),
        limit: int = typer.Option(50, "--limit", "-l", help="Сколько монет загрузить")
):
    console = Console()
    try:
        provider = get_provider(source)

        coins = provider.fetch_top_coins(limit=limit)
        console.print(f"[green]✓ Загружено {len(coins)} монет через {provider.get_name()}[/green]")

        portfolio = CryptoPortfolio(coins)

        if settings.storage == StorageType.JSON:
            storage = JsonStorage()
        elif settings.storage == StorageType.SQLITE:
            storage = SqliteStorage()
        else:
            raise ValueError(f"Неизвестное хранилище: {settings.storage}")

        reporter = get_reporter(output, storage=storage)
        reporter.report(portfolio, provider.get_name(), top_count=top)

    except ValueError as e:
        console.print(f"[red]❌ Ошибка!: {e}[/red]")
        raise typer.Exit(code=1)
    except Exception as e:
        console.print(f"[red]❌ Непредвиденная ошибка: {e}[/red]")
        raise typer.Exit(code=1)


@app.command()
def list_cadr():
    console = Console()
    storage = SqliteStorage()
    cadr = storage.list_cadr()

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
    storage = SqliteStorage()
    rows = storage.compare_cadr(id1, id2)

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

        diff_str = f"[green]+${diff:,.2f}[/green]" if diff > 0 else f"[red]-${abs(diff):,.2f}[/red]"

        table.add_row(symbol, f"${old_price:,.2f}", f"${new_price:,.2f}", diff_str)

    console.print(table)

if __name__ == "__main__":
    app()