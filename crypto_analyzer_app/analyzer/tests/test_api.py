from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.db import reset_queries
from django.test import TestCase

from analyzer.models import Balance, Coin, CoinPrice, Portfolio, Snapshot, WatchlistItem

User = get_user_model()


class WatchlistAPI(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="tester", password="testpass123")
        response = self.client.post("/api/token/", {"username": "tester", "password": "testpass123"})
        self.token = response.json()["access"]
        self.auth_header = f"Bearer {self.token}"
        cache.clear()

    def test_unauthenticated_access(self):
        response = self.client.get("/api/v1/watchlist/")
        self.assertEqual(response.status_code, 401)

    def test_authenticated_access(self):
        response = self.client.get("/api/v1/watchlist/", HTTP_AUTHORIZATION=self.auth_header)
        self.assertEqual(response.status_code, 200)

    @patch("analyzer.serializer.validate_symbol")
    def test_add_to_watchlist(self, mock_validate):
        mock_validate.return_value = {"valid": True, "name": "Bitcoin"}

        response = self.client.post(
            "/api/v1/watchlist/", {"symbol": "btc"}, content_type="application/json", HTTP_AUTHORIZATION=self.auth_header
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["coin"], "Bitcoin")

    def test_watchlist_query_count(self):
        coin_one = Coin.objects.create(name="Bobrcoin", symbol="bobr")
        coin_two = Coin.objects.create(name="Tarcoin", symbol="bsg")
        WatchlistItem.objects.create(user=self.user, coin=coin_one)
        WatchlistItem.objects.create(user=self.user, coin=coin_two)

        reset_queries()

        with self.assertNumQueries(3):
            response = self.client.get("/api/v1/watchlist/", HTTP_AUTHORIZATION=self.auth_header)

        self.assertEqual(response.status_code, 200)


class AnalyticsAPITest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="tester", password="testpass123")
        cache.clear()

    def test_market_stats_structure(self):
        snapshot = Snapshot.objects.create(provider="test", total_coins=2, total_market_cap=150001.00)
        coin = Coin.objects.create(name="Babkacoin", symbol="bkc")
        CoinPrice.objects.create(coin=coin, snapshot=snapshot, price=50001, volume_24h=1000004, change_24h=5.5)
        response = self.client.get("/api/v1/analytics/market-stats/")
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertEqual(data["snapshot_id"], snapshot.id)
        self.assertEqual(data["provider"], "test")
        self.assertEqual(data["min_price"], 50001.0)
        self.assertEqual(data["max_price"], 50001.0)
        self.assertEqual(data["total_market_cap"], 150001.0)

    def test_market_stats_empty(self):
        response = self.client.get("/api/v1/analytics/market-stats/")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["error"], "Снимков нет!")

    def test_top_movers(self):
        snapshot = Snapshot.objects.create(provider="test", total_coins=2, total_market_cap=100)
        ntc = Coin.objects.create(name="Nitcoin", symbol="ntc")
        pep = Coin.objects.create(name="Pepecoin", symbol="pep")

        CoinPrice.objects.create(coin=ntc, snapshot=snapshot, price=200, volume_24h=1, change_24h=5.0)
        CoinPrice.objects.create(coin=pep, snapshot=snapshot, price=200, volume_24h=2, change_24h=10.0)

        response = self.client.get("/api/v1/analytics/top-movers/")
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertEqual(len(data), 2)
        self.assertEqual(data[0]["coin_symbol"], "pep")
        self.assertEqual(data[1]["coin_symbol"], "ntc")

    def test_volume_toper_empty(self):
        response = self.client.get("/api/v1/analytics/volume-leaders/")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["error"], "Снимков нет!")

    def test_coins_filter_price_range(self):
        snapshot = Snapshot.objects.create(provider="test", total_coins=2, total_market_cap=100000)
        ntc = Coin.objects.create(name="Nitcoin", symbol="ntc")
        pep = Coin.objects.create(name="Pepecoin", symbol="pep")

        CoinPrice.objects.create(coin=ntc, snapshot=snapshot, price=50000, volume_24h=1, change_24h=1)
        CoinPrice.objects.create(coin=pep, snapshot=snapshot, price=2, volume_24h=1, change_24h=1)

        response = self.client.get("/api/v1/coins/?min_price=100")
        self.assertEqual(response.status_code, 200)
        results = response.json()
        if isinstance(results, list):
            self.assertEqual(len(results), 1)
            self.assertEqual(results[0]["symbol"], "ntc")
        else:
            self.assertEqual(len(results["results"]), 1)
            self.assertEqual(results["results"][0]["symbol"], "ntc")

        response = self.client.get("/api/v1/coins/?max_price=50")
        self.assertEqual(response.status_code, 200)
        results = response.json()
        if isinstance(results, list):
            self.assertEqual(len(results), 1)
            self.assertEqual(results[0]["symbol"], "pep")
        else:
            self.assertEqual(len(results["results"]), 1)
            self.assertEqual(results["results"][0]["symbol"], "pep")


class CeleryAPITest(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(username="admin", password="123321")
        self.client.force_login(self.admin)

    def test_start_task_snapshot(self):
        url = "/api/v1/snapshots/start/"
        response = self.client.post(url, data={"provider": "test", "limit": 2}, content_type="application/json")
        self.assertEqual(response.status_code, 202)
        result = response.json()
        self.assertIn("task_id", result)

    def test_task_status(self):
        url = "/api/v1/snapshots/start/"
        response = self.client.post(url, data={"provider": "test", "limit": 2}, content_type="application/json")
        task_id = response.json()["task_id"]

        status_url = f"/api/v1/snapshots/tasks/{task_id}/"
        status_response = self.client.get(status_url)
        self.assertEqual(status_response.status_code, 200)
        self.assertIn("status", status_response.json())


class ThrottleTests(TestCase):
    def setUp(self):
        cache.clear()  # сбрасываем счётчики throttle перед каждым тестом

    def test_anon_throttle_5_per_minute(self):
        url = "/api/v1/coins/"
        for i in range(5):
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200, f"Request {i + 1} should pass")

        response = self.client.get(url)  # 6-й запрос
        self.assertEqual(response.status_code, 429, "6th anonymous request should be throttled")

    def test_user_throttle_100_per_minute(self):
        user = User.objects.create_user(username="throttleuser", password="123")
        self.client.force_login(user)  # Session auth

        url = "/api/v1/coins/"
        for i in range(100):
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200, f"Request {i + 1} should pass")

        response = self.client.get(url)  # 101-й
        self.assertEqual(response.status_code, 429)


class PortfolioAPITest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="portfolio_user",
            password="testpass123",
        )

        response = self.client.post(
            "/api/token/",
            {
                "username": "portfolio_user",
                "password": "testpass123",
            },
        )

        self.token = response.json()["access"]
        self.auth_header = f"Bearer {self.token}"

        self.coin = Coin.objects.create(
            name="Bitcoin",
            symbol="BTC",
        )

        self.snapshot = Snapshot.objects.create(
            provider="test",
            total_coins=1,
            total_market_cap=100000,
        )

        CoinPrice.objects.create(
            coin=self.coin,
            snapshot=self.snapshot,
            price=Decimal("50000"),
            volume_24h=Decimal("1000000"),
            change_24h=Decimal("5"),
        )

        self.balance = Balance.objects.create(
            user=self.user,
            amount=Decimal("100000"),
        )

    def test_portfolio_requires_authentication(self):
        response = self.client.get("/api/v1/portfolio/")

        self.assertEqual(response.status_code, 401)

    def test_portfolio_list(self):
        Portfolio.objects.create(
            user=self.user,
            coin=self.coin,
            amount=Decimal("1.5"),
            buy_price=Decimal("40000"),
        )

        response = self.client.get(
            "/api/v1/portfolio/",
            HTTP_AUTHORIZATION=self.auth_header,
        )

        self.assertEqual(response.status_code, 200)

        data = response.json()

        self.assertEqual(data["count"], 1)

        position = data["results"][0]

        self.assertEqual(position["coin"], "Bitcoin")
        self.assertEqual(position["symbol"], "BTC")
        self.assertEqual(position["amount"], "1.500000000000")
        self.assertEqual(position["buy_price"], "40000.000000000000")
        self.assertEqual(position["current_price"], 50000.0)
        self.assertEqual(position["current_value"], 75000.0)

    def test_buy_success(self):
        response = self.client.post(
            "/api/v1/portfolio/buy/",
            {
                "coin": self.coin.id,
                "amount": "1",
            },
            content_type="application/json",
            HTTP_AUTHORIZATION=self.auth_header,
        )

        self.assertEqual(response.status_code, 200)

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

    def test_buy_insufficient_balance(self):
        response = self.client.post(
            "/api/v1/portfolio/buy/",
            {
                "coin": self.coin.id,
                "amount": "3",
            },
            content_type="application/json",
            HTTP_AUTHORIZATION=self.auth_header,
        )

        self.assertEqual(response.status_code, 400)

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

    def test_sell_success(self):
        Portfolio.objects.create(
            user=self.user,
            coin=self.coin,
            amount=Decimal("2"),
            buy_price=Decimal("40000"),
        )

        response = self.client.post(
            "/api/v1/portfolio/sell/",
            {
                "coin": self.coin.id,
                "amount": "0.5",
            },
            content_type="application/json",
            HTTP_AUTHORIZATION=self.auth_header,
        )

        self.assertEqual(response.status_code, 200)

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

    def test_sell_insufficient_portfolio(self):
        Portfolio.objects.create(
            user=self.user,
            coin=self.coin,
            amount=Decimal("1"),
            buy_price=Decimal("40000"),
        )

        response = self.client.post(
            "/api/v1/portfolio/sell/",
            {
                "coin": self.coin.id,
                "amount": "2",
            },
            content_type="application/json",
            HTTP_AUTHORIZATION=self.auth_header,
        )

        self.assertEqual(response.status_code, 400)

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

    def test_portfolio_summary(self):
        Portfolio.objects.create(
            user=self.user,
            coin=self.coin,
            amount=Decimal("1.5"),
            buy_price=Decimal("40000"),
        )

        response = self.client.get(
            "/api/v1/portfolio/summary/",
            HTTP_AUTHORIZATION=self.auth_header,
        )

        self.assertEqual(response.status_code, 200)

        data = response.json()["data"]

        self.assertEqual(
            data["balance"],
            "100000.000000000000",
        )

        self.assertEqual(
            data["portfolio_value"],
            "75000.000000000000",
        )

        self.assertEqual(
            data["total_value"],
            "175000.000000000000",
        )

    def test_summary_requires_authentication(self):
        response = self.client.get(
            "/api/v1/portfolio/summary/",
        )

        self.assertEqual(response.status_code, 401)

    def test_buy_validation(self):
        response = self.client.post(
            "/api/v1/portfolio/buy/",
            {
                "coin": self.coin.id,
                "amount": "0",
            },
            content_type="application/json",
            HTTP_AUTHORIZATION=self.auth_header,
        )

        self.assertEqual(response.status_code, 400)

    def test_sell_validation(self):
        response = self.client.post(
            "/api/v1/portfolio/sell/",
            {
                "coin": self.coin.id,
                "amount": "0",
            },
            content_type="application/json",
            HTTP_AUTHORIZATION=self.auth_header,
        )

        self.assertEqual(response.status_code, 400)

    def test_user_sees_only_own_portfolio(self):
        another_user = User.objects.create_user(
            username="another_user",
            password="testpass123",
        )

        Portfolio.objects.create(
            user=self.user,
            coin=self.coin,
            amount=Decimal("1"),
            buy_price=Decimal("40000"),
        )

        another_coin = Coin.objects.create(
            name="Ethereum",
            symbol="ETH",
        )

        Portfolio.objects.create(
            user=another_user,
            coin=another_coin,
            amount=Decimal("10"),
            buy_price=Decimal("3000"),
        )

        response = self.client.get(
            "/api/v1/portfolio/",
            HTTP_AUTHORIZATION=self.auth_header,
        )

        self.assertEqual(response.status_code, 200)

        data = response.json()

        self.assertEqual(data["count"], 1)
        self.assertEqual(data["results"][0]["coin"], "Bitcoin")

    def test_user_cannot_sell_another_users_portfolio(self):
        another_user = User.objects.create_user(
            username="another_user",
            password="testpass123",
        )

        another_balance = Balance.objects.create(
            user=another_user,
            amount=Decimal("0"),
        )

        Portfolio.objects.create(
            user=another_user,
            coin=self.coin,
            amount=Decimal("2"),
            buy_price=Decimal("40000"),
        )

        response = self.client.post(
            "/api/v1/portfolio/sell/",
            {
                "coin": self.coin.id,
                "amount": "1",
            },
            content_type="application/json",
            HTTP_AUTHORIZATION=self.auth_header,
        )

        self.assertEqual(response.status_code, 400)

        portfolio = Portfolio.objects.get(
            user=another_user,
            coin=self.coin,
        )

        another_balance.refresh_from_db()

        self.assertEqual(
            portfolio.amount,
            Decimal("2"),
        )

        self.assertEqual(
            another_balance.amount,
            Decimal("0"),
        )
