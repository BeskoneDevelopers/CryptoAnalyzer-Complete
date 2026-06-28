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
            "generate_AT": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
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


    def sweet_table(self):
        #Верхушка топа
        top_upper_table = Table(
            title="Топ 3 лидера роста",
            style="green",
        )
        top_upper_table.add_column("Коин", style="cyan")
        top_upper_table.add_column("Символ", style="blue")
        top_upper_table.add_column("Изменение за 24ч", style="green")

        for coin in self.result["top_coin"]:
            change = coin["change_24h"]
            change_str = f"+{change:.2f}%" if change else "N/A"
            top_upper_table.add_row(coin['name'], coin['symbol'], change_str)

        self.console.print(top_upper_table)

        #Донные лидеры
        top_down_table = Table(
            title="Топ 3 лидера падения",
            style="red"
        )
        top_down_table.add_column("Коин", style="cyan")
        top_down_table.add_column("Символ", style="yellow")
        top_down_table.add_column("Изменение за 24ч", style="red")

        for coin in self.result["top_down_coin"]:
            change = coin["change_24h"]
            change_str = f"{change:.2f}%" if change else "N/A"
            top_down_table.add_row(coin['name'], coin['symbol'], change_str)

        self.console.print(top_down_table)

        #Максимальный обьем торгов
        value = self.result["highest_volume"]
        self.console.print(Panel(
            f"[bold]Максимальный объем торгов[/bold]\n"
            f"Монета: [cyan]{value['name']}[/cyan] ([yellow]{value['symbol']}[/yellow])\n"
            f"Объем: [green]${value['volume']:,.0f}[/green]",
            border_style="blue"
        ))

        #Сумма капитализации
        total_cap = self.result["total_market_cap"]
        self.console.print(Panel(
            f"[bold]Суммарная капитализация топ-50[/bold]\n"
            f"[green]{total_cap}[/green]",
            border_style="green"
        ))

    def save_result(self, filename: str = "Отчет_крипты.json"):
        with open(filename, "w", encoding="utf-8") as file:
            json.dump(
                self.result,
                file,
                indent=4,
                ensure_ascii=False
            )

    def run(self):
        with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                transient=True,
        ) as progress:

            # Имитируем процесс загрузки
            task = progress.add_task("[cyan]Загрузка данных с CoinGecko...", total=None)

            try:
                self.data = self.featch_market()
                progress.update(task, description="[green]Данные загружены!")
                time.sleep(0.5)

            except Exception as e:
                progress.update(task, description="[red]Ошибка загрузки данных!")
                self.console.print(f"[red]Ошибка: {e}[/red]")
                return

            task2 = progress.add_task("[yellow]Анализ данных...", total=None)
            self.analyze_data()
            progress.update(task2, description="[green]Анализ завершен!")
            time.sleep(0.5)

        # Выводим результаты
        self.sweet_table()

        # Сохраняем отчет
        self.save_result()

        self.console.print("\n[bold green]Анализ завершен[/bold green]")


def main():
    analyzer = Analyzer()
    try:
        analyzer.run()
    except KeyboardInterrupt:
        print("\nПрограмма прервана пользователем")
    except Exception as e:
        print(f"Произошла ошибка: {e}")


if __name__ == "__main__":
    main()