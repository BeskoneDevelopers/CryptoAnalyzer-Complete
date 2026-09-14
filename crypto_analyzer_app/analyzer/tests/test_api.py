from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.db import reset_queries
from django.test import TestCase
from django.http import Http404

from analyzer.models import Coin, CoinPrice, Snapshot, WatchlistItem
from analyzer.exceptions import custom_exception_handler

from rest_framework.exceptions import MethodNotAllowed

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

    @patch("analyzer.views.AsyncResult")
    def test_task_status(self, mock_async_result):
        mock_result = MagicMock()
        mock_result.status = "PENDING"
        mock_result.result = None
        mock_async_result.return_value = mock_result

        response = self.client.get("/api/v1/snapshots/tasks/123/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "PENDING")


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

class AnyTests(TestCase):

    def test_custom_exception_handler_handles_django_http404(self):
        response = custom_exception_handler(Http404(), {})

        assert response.status_code == 404
        assert response.data["success"] is False
        assert response.data["error"]["code"] == "not_found"

    def test_custom_exception_handler_returns_json_for_unknown_error(self):
        response = custom_exception_handler(RuntimeError("boom"), {})

        assert response.status_code == 500
        assert response.data["success"] is False
        assert response.data["error"]["code"] == "server_error"

    def test_custom_exception_handler_uses_request_method_for_method_not_allowed(self):
        request = type("Request", (), {"method": "POST"})()

        response = custom_exception_handler(
            MethodNotAllowed("POST"),
            {"request": request},
        )

        assert response.status_code == 405
        assert response.data["error"]["code"] == "method_not_allowed"
        assert response.data["error"]["message"] == "Метод POST не разрешён"