from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from analyzer.models import Coin, CoinPrice, Snapshot


class Command(BaseCommand):
    help = "Заполняет таблицы тестовыми данными"

    def handle(self, *args, **options):
        with transaction.atomic():
            self._create_coins()
            self._create_snapshots()
            self._create_coinprices()

    def _create_coins(self):
        create_count = 0
        for i in range(1, 101):
            name = f"BC_{i}"
            symbol = name
            _, created = Coin.objects.get_or_create(symbol=symbol, defaults={"name": name})

            if created:
                create_count += 1

        self.stdout.write(f"Добавлено - {create_count} монет")

    def _create_snapshots(self):
        provider = "benchmark"
        total_coins = 100
        total_market_cap = Decimal("1000.0")
        snapshots = []

        count_point = Snapshot.objects.filter(provider=provider).count()

        if count_point == 500:
            self.stdout.write("Таблица заполнена")
            return

        Snapshot.objects.filter(provider=provider).delete()
        for _ in range(500):
            snapshots.append(
                Snapshot(
                    provider=provider,
                    total_coins=total_coins,
                    total_market_cap=total_market_cap,
                )
            )

        Snapshot.objects.bulk_create(snapshots)

    def _create_coinprices(self):
        coin_prices = []

        snapshot_provider = "benchmark"
        search_symbol = "BC_"
        price = Decimal("1.0")
        volume_24h = Decimal("2.0")
        change_24h = Decimal("4.0")

        benchmark_coins = Coin.objects.filter(symbol__startswith=search_symbol)
        benchmark_snapshot = Snapshot.objects.filter(provider=snapshot_provider)

        CoinPrice.objects.filter(coin__symbol__startswith=search_symbol, snapshot__provider=snapshot_provider).delete()

        for snapshot in benchmark_snapshot:
            for coin in benchmark_coins:
                coin_prices.append(
                    CoinPrice(
                        coin=coin,
                        snapshot=snapshot,
                        price=price,
                        volume_24h=volume_24h,
                        change_24h=change_24h,
                    )
                )

        self.stdout.write(f"Количество монет: {benchmark_coins.count()}")
        self.stdout.write(f"Количество снимков: {benchmark_snapshot.count()}")

        CoinPrice.objects.bulk_create(coin_prices, batch_size=1000)

        self.stdout.write(f"Создано CoinPrice: {len(coin_prices)}")
