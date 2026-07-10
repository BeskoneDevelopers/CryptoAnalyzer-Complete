import typer
from rich.console import Console


from models.portfolio import CryptoPortfolio
from providers import get_provider
from reporters import get_reporter


from settings import settings, StorageType
from storage.json_storage import JsonStorage

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
        #elif settings.storage == StorageType.SQLITE:
            #storage = SqliteStorage()
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

if __name__ == "__main__":
    app()