from decimal import Decimal
from threading import Barrier, Thread
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.db import close_old_connections
from django.test import TestCase, TransactionTestCase

from analyzer.models import Balance, Coin, Portfolio
from atomic_tasks.services import PortfolioService

User = get_user_model()


class PortfolioServiceTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="test_user",
            password="password123",
        )

        self.coin = Coin.objects.create(
            name="Bitcoin",
            symbol="BTC",
        )

        self.balance = Balance.objects.create(
            user=self.user,
            amount=Decimal("100000"),
        )

    @patch(
        "atomic_tasks.services.get_latest_price",
        return_value=Decimal("50000"),
    )
    def test_buy_success(self, mock_price):
        PortfolioService.buy(
            user=self.user,
            coin=self.coin,
            amount=Decimal("1"),
        )

        self.balance.refresh_from_db()

        portfolio = Portfolio.objects.get(
            user=self.user,
            coin=self.coin,
        )

        self.assertEqual(
            self.balance.amount,
            Decimal("50000"),
        )
        self.assertEqual(
            portfolio.amount,
            Decimal("1"),
        )
        self.assertEqual(
            portfolio.buy_price,
            Decimal("50000"),
        )

    @patch(
        "atomic_tasks.services.get_latest_price",
        return_value=Decimal("50000"),
    )
    def test_buy_insufficient_balance_rollback(self, mock_price):
        with self.assertRaises(ValueError):
            PortfolioService.buy(
                user=self.user,
                coin=self.coin,
                amount=Decimal("3"),
            )

        self.balance.refresh_from_db()

        self.assertEqual(
            self.balance.amount,
            Decimal("100000"),
        )

        self.assertFalse(
            Portfolio.objects.filter(
                user=self.user,
                coin=self.coin,
            ).exists()
        )

    @patch(
        "atomic_tasks.services.get_latest_price",
        return_value=Decimal("50000"),
    )
    def test_sell_success(self, mock_price):
        Portfolio.objects.create(
            user=self.user,
            coin=self.coin,
            amount=Decimal("2"),
            buy_price=Decimal("40000"),
        )

        PortfolioService.sell(
            user=self.user,
            coin=self.coin,
            amount=Decimal("0.5"),
        )

        self.balance.refresh_from_db()

        portfolio = Portfolio.objects.get(
            user=self.user,
            coin=self.coin,
        )

        self.assertEqual(
            self.balance.amount,
            Decimal("125000"),
        )
        self.assertEqual(
            portfolio.amount,
            Decimal("1.5"),
        )
        self.assertEqual(
            portfolio.buy_price,
            Decimal("40000"),
        )

    @patch(
        "atomic_tasks.services.get_latest_price",
        return_value=Decimal("50000"),
    )
    def test_sell_insufficient_portfolio_rollback(self, mock_price):
        Portfolio.objects.create(
            user=self.user,
            coin=self.coin,
            amount=Decimal("1"),
            buy_price=Decimal("40000"),
        )

        with self.assertRaises(ValueError):
            PortfolioService.sell(
                user=self.user,
                coin=self.coin,
                amount=Decimal("2"),
            )

        self.balance.refresh_from_db()

        portfolio = Portfolio.objects.get(
            user=self.user,
            coin=self.coin,
        )

        self.assertEqual(
            self.balance.amount,
            Decimal("100000"),
        )
        self.assertEqual(
            portfolio.amount,
            Decimal("1"),
        )


class PortfolioConcurrentTestCase(TransactionTestCase):
    reset_sequences = True

    def setUp(self):
        self.user = User.objects.create_user(
            username="concurrent_user",
            password="password123",
        )

        self.coin = Coin.objects.create(
            name="Bitcoin",
            symbol="BTC",
        )

        Balance.objects.create(
            user=self.user,
            amount=Decimal("50000"),
        )

    @patch(
        "atomic_tasks.services.get_latest_price",
        return_value=Decimal("50000"),
    )
    def test_concurrent_buy(self, mock_price):
        barrier = Barrier(2)
        errors = []

        def make_purchase():
            try:
                close_old_connections()
                barrier.wait()
                PortfolioService.buy(
                    user=self.user,
                    coin=self.coin,
                    amount=Decimal("1"),
                )
            except ValueError as error:
                errors.append(error)
            finally:
                close_old_connections()

        thread1 = Thread(target=make_purchase)
        thread2 = Thread(target=make_purchase)

        thread1.start()
        thread2.start()

        thread1.join()
        thread2.join()

        balance = Balance.objects.get(user=self.user)
        portfolio = Portfolio.objects.get(
            user=self.user,
            coin=self.coin,
        )

        assert balance.amount == Decimal("0")
        assert portfolio.amount == Decimal("1")
        assert len(errors) == 1
        assert isinstance(errors[0], ValueError)
