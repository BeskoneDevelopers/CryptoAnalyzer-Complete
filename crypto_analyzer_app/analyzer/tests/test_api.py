from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from analyzer.models import Coin, CoinPrice, Snapshot, WatchlistItem

User = get_user_model()


class WatchlistAPI(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="tester", password="testpass123")
        response = self.client.post("/api/token/", {"username": "tester", "password": "testpass123"})
        self.token = response.json()["access"]
        self.auth_header = f"Bearer {self.token}"

    def test_unauthenticated_access(self):
        response = self.client.get("/api/watchlist/")
        self.assertEqual(response.status_code, 401)

    def test_authenticated_access(self):
        response = self.client.get("/api/watchlist/", HTTP_AUTHORIZATION=self.auth_header)
        self.assertEqual(response.status_code, 200)

    @patch("analyzer.serializer.service_validate_symbol")
    def test_add_to_watchlist(self, mock_validate):
        mock_validate.return_value = {
            "valid": True,
            "name": "Bitcoin",
        }

        response = self.client.post(
            "/api/watchlist/",
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

    def test_watchlist_query_count(self):
        coin_one = Coin.objects.create(name="Bobrcoin", symbol="bobr")
        coin_two = Coin.objects.create(name="Tarcoin", symbol="bsg")
        WatchlistItem.objects.create(user=self.user, coin=coin_one)
        WatchlistItem.objects.create(user=self.user, coin=coin_two)

        with self.assertNumQueries(3):
            response = self.client.get(
                "/api/watchlist/",
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
            "/api/watchlist/",
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
            "/api/watchlist/",
            HTTP_AUTHORIZATION=auth_header_b,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["count"], 0)
        self.assertEqual(response.json()["results"], [])

    def test_remove_nonexistent_watchlist_item(self):
        response = self.client.delete(
            "/api/watchlist/remove/",
            {"symbol": "btc"},
            content_type="application/json",
            HTTP_AUTHORIZATION=self.auth_header,
        )

        self.assertEqual(response.status_code, 404)


class AnalyticsAPITest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="tester", password="testpass123")

    def test_market_stats_structure(self):
        snapshot = Snapshot.objects.create(provider="test", total_coins=2, total_market_cap=150001.00)
        coin1 = Coin.objects.create(name="Babkacoin", symbol="bkc")
        coin2 = Coin.objects.create(name="MotoMoto", symbol="mot")

        CoinPrice.objects.create(coin=coin1, snapshot=snapshot, price=50001, volume_24h=1000004, change_24h=5.5)
        CoinPrice.objects.create(coin=coin2, snapshot=snapshot, price=102312, volume_24h=984322, change_24h=4.1)

        response = self.client.get("/api/analytics/market-stats/")
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertEqual(data["snapshot_id"], snapshot.id)
        self.assertEqual(data["provider"], "test")
        self.assertEqual(data["min_price"], 50001.0)
        self.assertEqual(data["max_price"], 102312.0)
        self.assertEqual(data["total_market_cap"], 150001.0)
        self.assertEqual(data["avg_price"], 76156.5)

    def test_market_stats_empty(self):
        response = self.client.get("/api/analytics/market-stats/")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["error"], "Снимков нет!")

    def test_top_movers(self):
        snapshot = Snapshot.objects.create(provider="test", total_coins=2, total_market_cap=100)
        ntc = Coin.objects.create(name="Nitcoin", symbol="ntc")
        pep = Coin.objects.create(name="Pepecoin", symbol="pep")

        CoinPrice.objects.create(coin=ntc, snapshot=snapshot, price=200, volume_24h=1, change_24h=5.0)
        CoinPrice.objects.create(coin=pep, snapshot=snapshot, price=200, volume_24h=2, change_24h=10.0)

        response = self.client.get("/api/analytics/top-movers/")
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertEqual(len(data), 2)
        self.assertEqual(data[0]["coin_symbol"], "pep")
        self.assertEqual(data[1]["coin_symbol"], "ntc")

    def test_volume_leaders(self):
        snapshot = Snapshot.objects.create(provider="test", total_coins=2, total_market_cap=100)
        ntc = Coin.objects.create(name="Nitcoin", symbol="ntc")
        pep = Coin.objects.create(name="Pepecoin", symbol="pep")

        CoinPrice.objects.create(coin=ntc, snapshot=snapshot, price=200, volume_24h=100, change_24h=5.0)
        CoinPrice.objects.create(coin=pep, snapshot=snapshot, price=300, volume_24h=500, change_24h=10.0)

        response = self.client.get("/api/analytics/volume-leaders/")
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertEqual(len(data), 2)
        self.assertEqual(data[0]["coin_symbol"], "pep")
        self.assertEqual(data[1]["coin_symbol"], "ntc")

    def test_top_movers_empty_snapshot(self):
        response = self.client.get("/api/analytics/top-movers/")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["error"], "Снимков нет!")

    def test_volume_toper_empty(self):
        response = self.client.get("/api/analytics/volume-leaders/")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["error"], "Снимков нет!")

    def test_coins_filter_price_range(self):
        snapshot = Snapshot.objects.create(provider="test", total_coins=2, total_market_cap=100000)
        ntc = Coin.objects.create(name="Nitcoin", symbol="ntc")
        pep = Coin.objects.create(name="Pepecoin", symbol="pep")

        CoinPrice.objects.create(coin=ntc, snapshot=snapshot, price=50000, volume_24h=1, change_24h=1)
        CoinPrice.objects.create(coin=pep, snapshot=snapshot, price=2, volume_24h=1, change_24h=1)

        response = self.client.get("/api/coins/?min_price=100")
        self.assertEqual(response.status_code, 200)

        results = response.json()["results"]
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["symbol"], "ntc")

        response = self.client.get("/api/coins/?max_price=50")
        self.assertEqual(response.status_code, 200)

        results = response.json()["results"]
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["symbol"], "pep")


class CeleryAPITest(TestCase):
    @patch("analyzer.tasks._fetch_data")
    def test_start_task_snapshot(self, mock_fetch):
        mock_fetch.return_value = [
            {
                "name": "Bitcoin",
                "symbol": "btc",
                "current_price": 50000,
                "total_volume": 1000000,
                "price_change_percentage_24h": 5,
            },
            {
                "name": "Ethereum",
                "symbol": "eth",
                "current_price": 3000,
                "total_volume": 500000,
                "price_change_percentage_24h": 3,
            },
        ]
        response = self.client.post(
            "/api/snapshots/start/", data={"provider": "coingecko", "limit": 2}, content_type="application/json"
        )
        self.assertEqual(response.status_code, 202)
        data = response.json()
        self.assertIn("task_id", data)

        self.assertIn("task_id", data)

        snapshot = Snapshot.objects.get(provider="coingecko")
        self.assertEqual(snapshot.total_coins, 2)
        self.assertEqual(CoinPrice.objects.filter(snapshot=snapshot).count(), 2)
        mock_fetch.assert_called_once_with("coingecko", 2)

    @patch("analyzer.tasks._fetch_data")
    def test_task_status(self, mock_featch):

        mock_featch.return_value = [
            {
                "name": "Jambo",
                "symbol": "jmb",
                "current_price": 62345632.0,
                "total_volume": 124323.0,
                "price_change_percentage_24h": 11.2,
            }
        ]
        url = "/api/snapshots/start/"

        response = self.client.post(url, data={"provider": "coingecko", "limit": 1}, content_type="application/json")
        self.assertEqual(response.status_code, 202)
        task_id = response.json()["task_id"]

        status_url = f"/api/snapshots/tasks/{task_id}/"
        status_response = self.client.get(status_url)

        self.assertEqual(status_response.status_code, 200)

        data = status_response.json()
        self.assertEqual(data["status"], "SUCCESS")
        self.assertEqual(data["result"]["total_coins"], 1)
        mock_featch.assert_called_once_with("coingecko", 1)

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
