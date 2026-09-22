from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.db import reset_queries
from django.http import Http404
from django.test import SimpleTestCase, TestCase
from rest_framework.exceptions import (
    MethodNotAllowed,
    NotAuthenticated,
    PermissionDenied,
    Throttled,
    ValidationError,
)

from analyzer.exceptions import custom_exception_handler
from analyzer.models import Balance, Coin, CoinPrice, Portfolio, Snapshot, WatchlistItem

User = get_user_model()


@pytest.mark.integration
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

    @patch("analyzer.serializer.service_validate_symbol")
    def test_add_to_watchlist(self, mock_validate):
        mock_validate.return_value = {
            "valid": True,
            "name": "Bitcoin",
        }

        response = self.client.post(
            "/api/v1/watchlist/",
            {"symbol": "btc"},
            content_type="application/json",
            HTTP_AUTHORIZATION=self.auth_header,
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["coin"], "Bitcoin")
        self.assertEqual(
            WatchlistItem.objects.filter(
                user=self.user,
                coin__symbol="BTC",
            ).count(),
            1,
        )

        mock_validate.assert_called_once_with("BTC")

    def test_watchlist_query_count(self):
        coin_one = Coin.objects.create(name="Bobrcoin", symbol="bobr")
        coin_two = Coin.objects.create(name="Tarcoin", symbol="bsg")
        WatchlistItem.objects.create(user=self.user, coin=coin_one)
        WatchlistItem.objects.create(user=self.user, coin=coin_two)

        reset_queries()
        with self.assertNumQueries(3):
            response = self.client.get(
                "/api/v1/watchlist/",
                HTTP_AUTHORIZATION=self.auth_header,
            )

        self.assertEqual(response.status_code, 200)

    @patch("analyzer.serializer.service_validate_symbol")
    def test_user_isolation(self, mock_validate):
        mock_validate.return_value = {
            "valid": True,
            "name": "Bitcoin",
        }

        response = self.client.post(
            "/api/v1/watchlist/",
            {"symbol": "btc"},
            content_type="application/json",
            HTTP_AUTHORIZATION=self.auth_header,
        )

        self.assertEqual(response.status_code, 201)

        User.objects.create_user(
            username="tester2",
            password="testpass123",
        )

        response = self.client.post(
            "/api/token/",
            {
                "username": "tester2",
                "password": "testpass123",
            },
        )

        token_b = response.json()["access"]
        auth_header_b = f"Bearer {token_b}"

        response = self.client.get(
            "/api/v1/watchlist/",
            HTTP_AUTHORIZATION=auth_header_b,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["count"], 0)
        self.assertEqual(response.json()["results"], [])

    def test_remove_nonexistent_watchlist_item(self):
        response = self.client.delete(
            "/api/v1/watchlist/remove/",
            {"symbol": "btc"},
            content_type="application/json",
            HTTP_AUTHORIZATION=self.auth_header,
        )

        self.assertEqual(response.status_code, 404)


@pytest.mark.integration
class AnalyticsAPITest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="tester", password="testpass123")
        cache.clear()

    def test_market_stats_structure(self):
        snapshot = Snapshot.objects.create(provider="test", total_coins=2, total_market_cap=150001.00)

        coin1 = Coin.objects.create(name="Babkacoin", symbol="bkc")
        coin2 = Coin.objects.create(name="MotoMoto", symbol="mot")

        CoinPrice.objects.create(coin=coin1, snapshot=snapshot, price=50001, volume_24h=1000004, change_24h=5.5)
        CoinPrice.objects.create(coin=coin2, snapshot=snapshot, price=102312, volume_24h=984322, change_24h=4.1)

        response = self.client.get("/api/v1/analytics/market-stats/")
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertEqual(data["snapshot_id"], snapshot.id)
        self.assertEqual(data["provider"], "test")
        self.assertEqual(data["min_price"], 50001.0)
        self.assertEqual(data["max_price"], 102312.0)
        self.assertEqual(data["total_market_cap"], 150001.0)
        self.assertEqual(data["avg_price"], 76156.5)

    def test_market_stats_empty(self):
        response = self.client.get("/api/v1/analytics/market-stats/")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["code"], "not_found")
        self.assertEqual(response.json()["error"], "Запрашиваемый ресурс не найден")

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
        self.assertEqual(response.json()["code"], "not_found")

    def test_volume_leaders(self):
        snapshot = Snapshot.objects.create(provider="test", total_coins=2, total_market_cap=100)
        ntc = Coin.objects.create(name="Nitcoin", symbol="ntc")
        pep = Coin.objects.create(name="Pepecoin", symbol="pep")

        CoinPrice.objects.create(coin=ntc, snapshot=snapshot, price=200, volume_24h=100, change_24h=5.0)
        CoinPrice.objects.create(coin=pep, snapshot=snapshot, price=300, volume_24h=500, change_24h=10.0)

        response = self.client.get("/api/v1/analytics/volume-leaders/")
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertEqual(len(data), 2)
        self.assertEqual(data[0]["coin_symbol"], "pep")
        self.assertEqual(data[1]["coin_symbol"], "ntc")

    def test_top_movers_empty_snapshot(self):
        response = self.client.get("/api/v1/analytics/top-movers/")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["code"], "not_found")

    def test_coins_filter_price_range(self):
        snapshot = Snapshot.objects.create(provider="test", total_coins=2, total_market_cap=100000)
        ntc = Coin.objects.create(name="Nitcoin", symbol="ntc")
        pep = Coin.objects.create(name="Pepecoin", symbol="pep")

        CoinPrice.objects.create(coin=ntc, snapshot=snapshot, price=50000, volume_24h=1, change_24h=1)
        CoinPrice.objects.create(coin=pep, snapshot=snapshot, price=2, volume_24h=1, change_24h=1)

        response = self.client.get("/api/v1/coins/?min_price=100")
        self.assertEqual(response.status_code, 200)

        results = response.json()["results"]
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["symbol"], "ntc")

        response = self.client.get("/api/v1/coins/?max_price=50")
        self.assertEqual(response.status_code, 200)

        results = response.json()["results"]
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["symbol"], "pep")

    def test_coin_history_cursor_pagination(self):
        coin = Coin.objects.create(
            name="Bitcoin",
            symbol="btc",
        )

        for index in range(12):
            snapshot = Snapshot.objects.create(
                provider=f"test-{index}",
                total_coins=1,
                total_market_cap=1000 + index,
            )
            CoinPrice.objects.create(
                coin=coin,
                snapshot=snapshot,
                price=100 + index,
                volume_24h=1000 + index,
                change_24h=index,
            )

        response = self.client.get(f"/api/v1/coins/{coin.pk}/history/")

        self.assertEqual(response.status_code, 200)

        data = response.json()

        self.assertIn("results", data)
        self.assertIn("next", data)
        self.assertEqual(len(data["results"]), 10)

        self.assertIsNotNone(data["next"])


@pytest.mark.integration
class CeleryAPITest(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(
            username="admin",
            password="123321",
        )
        self.client.force_login(self.admin)

    @patch("analyzer.views.fetch_snapshot_task.delay")
    def test_start_task_snapshot(self, mock_delay):
        mock_task = MagicMock()
        mock_task.id = "test-task-id"
        mock_delay.return_value = mock_task

        response = self.client.post(
            "/api/v1/snapshots/start/",
            data={"provider": "test", "limit": 2},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.json()["task_id"], "test-task-id")
        mock_delay.assert_called_once_with("test", 2)

    @patch("analyzer.views.fetch_snapshot_task.AsyncResult")
    def test_task_status(self, mock_async_result):
        mock_result = MagicMock()
        mock_result.status = "PENDING"
        mock_result.result = None
        mock_result.failed.return_value = False
        mock_async_result.return_value = mock_result

        response = self.client.get("/api/v1/snapshots/tasks/123/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "PENDING")


@pytest.mark.integration
class ThrottleTests(TestCase):
    def setUp(self):
        cache.clear()  # сбрасываем счётчики throttle перед каждым тестом

    def test_anon_throttle_5_per_minute(self):
        url = "/api/v1/coins/"
        for i in range(5):
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200, f"Request {i + 1} should pass")

        response = self.client.get(url)
        self.assertEqual(response.status_code, 429, "6th anonymous request should be throttled")

    def test_user_throttle_100_per_minute(self):
        user = User.objects.create_user(username="throttleuser", password="123")
        self.client.force_login(user)

        url = "/api/v1/coins/"
        for i in range(100):
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200, f"Request {i + 1} should pass")
        response = self.client.get(url)
        self.assertEqual(
            response.status_code,
            429,
            "101st authenticated request should be throttled",
        )

    def test_admin_throttle_1000_per_minute(self):
        admin = User.objects.create_superuser(
            username="adminthrottle",
            password="123",
            email="admin@example.com",
        )
        self.client.force_login(admin)

        url = "/api/v1/coins/"

        for i in range(1000):
            response = self.client.get(url)
            self.assertEqual(
                response.status_code,
                200,
                f"Request {i + 1} should pass",
            )

        response = self.client.get(url)

        self.assertEqual(
            response.status_code,
            429,
            "1001st superuser request should be throttled",
        )


@pytest.mark.integration
class PortfolioAPITest(TestCase):
    def setUp(self):
        cache.clear()

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
            data["purchase_value"],
            "60000.000000000000",
        )

        self.assertEqual(
            data["profit_loss"],
            "15000.000000000000",
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

    def test_buy_without_balance(self):
        self.balance.delete()

        response = self.client.post(
            "/api/v1/portfolio/buy/",
            {
                "coin": self.coin.id,
                "amount": "1",
            },
            content_type="application/json",
            HTTP_AUTHORIZATION=self.auth_header,
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["code"], "validation_error")

    def test_sell_without_balance(self):
        self.balance.delete()

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
        self.assertEqual(response.json()["code"], "validation_error")

    def test_portfolio_without_current_price(self):
        coin = Coin.objects.create(
            name="Ethereum",
            symbol="ETH",
        )

        Portfolio.objects.create(
            user=self.user,
            coin=coin,
            amount=Decimal("2"),
            buy_price=Decimal("3000"),
        )

        response = self.client.get(
            "/api/v1/portfolio/",
            HTTP_AUTHORIZATION=self.auth_header,
        )

        self.assertEqual(response.status_code, 200)

        positions = response.json()["results"]

        ethereum = next(position for position in positions if position["symbol"] == "ETH")

        self.assertIsNone(ethereum["current_price"])
        self.assertIsNone(ethereum["current_value"])

    def test_summary_without_snapshot(self):
        Snapshot.objects.all().delete()

        response = self.client.get(
            "/api/v1/portfolio/summary/",
            HTTP_AUTHORIZATION=self.auth_header,
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["code"], "validation_error")

    def test_summary_without_balance(self):
        self.balance.delete()

        response = self.client.get(
            "/api/v1/portfolio/summary/",
            HTTP_AUTHORIZATION=self.auth_header,
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["code"], "validation_error")

    def test_summary_without_current_price(self):
        coin = Coin.objects.create(
            name="Ethereum",
            symbol="ETH",
        )

        Portfolio.objects.create(
            user=self.user,
            coin=coin,
            amount=Decimal("2"),
            buy_price=Decimal("3000"),
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
            data["purchase_value"],
            "6000.000000000000",
        )
        self.assertIsNone(data["portfolio_value"])
        self.assertIsNone(data["profit_loss"])
        self.assertIsNone(data["total_value"])


@pytest.mark.unit
class AnyTests(SimpleTestCase):
    def test_custom_exception_handler_handles_django_http404(self):
        response = custom_exception_handler(Http404(), {})

        assert response.status_code == 404
        assert response.data["code"] == "not_found"
        assert response.data["error"] == "Запрашиваемый ресурс не найден"

    def test_custom_exception_handler_returns_json_for_unknown_error(self):
        response = custom_exception_handler(RuntimeError("boom"), {})

        assert response.status_code == 500
        assert response.data["code"] == "server_error"
        assert response.data["error"] == "Ошибка сервера. Попробуйте позже"

    def test_custom_exception_handler_uses_request_method_for_method_not_allowed(self):
        request = type("Request", (), {"method": "POST"})()

        response = custom_exception_handler(
            MethodNotAllowed("POST"),
            {"request": request},
        )

        assert response.status_code == 405
        assert response.data["code"] == "method_not_allowed"
        assert response.data["error"] == "Метод POST не разрешён"

    def test_custom_exception_handler_validation_error(self):
        response = custom_exception_handler(
            ValidationError({"symbol": ["Это поле обязательно."]}),
            {},
        )

        assert response.status_code == 400
        assert response.data["code"] == "validation_error"
        assert response.data["error"] == "Ошибка валидации данных"

    def test_custom_exception_handler_not_authenticated(self):
        response = custom_exception_handler(NotAuthenticated(), {})

        assert response.status_code == 401
        assert response.data["code"] == "authentication_failed"
        assert response.data["error"] == "Требуется авторизация"

    def test_custom_exception_handler_permission_denied(self):
        response = custom_exception_handler(PermissionDenied(), {})

        assert response.status_code == 403
        assert response.data["code"] == "permission_denied"
        assert response.data["error"] == "У вас недостаточно прав"

    def test_custom_exception_handler_throttled_preserves_retry_after(self):
        response = custom_exception_handler(
            Throttled(wait=60),
            {},
        )

        assert response.status_code == 429
        assert response.data["code"] == "throttled"
        assert response.data["error"] == "Превышен лимит запросов"
        assert response["Retry-After"] == "60"


@pytest.mark.integration
class JWTIntegrationTest(TestCase):
    def test_refresh_token_cannot_be_reused_after_rotation(self):
        user = User.objects.create_user(
            username="jwt_user",
            password="test_password_123",
        )

        token_response = self.client.post(
            "/api/token/",
            {
                "username": user.username,
                "password": "test_password_123",
            },
            content_type="application/json",
        )

        self.assertEqual(token_response.status_code, 200)

        refresh = token_response.json()["refresh"]

        first_refresh = self.client.post(
            "/api/token/refresh/",
            {"refresh": refresh},
            content_type="application/json",
        )

        self.assertEqual(first_refresh.status_code, 200)

        second_refresh = self.client.post(
            "/api/token/refresh/",
            {"refresh": refresh},
            content_type="application/json",
        )

        self.assertEqual(second_refresh.status_code, 401)
