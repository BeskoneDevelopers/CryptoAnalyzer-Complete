from django.test import TestCase
from django.contrib.auth import get_user_model
from unittest.mock import patch

from analyzer.models import Coin, Snapshot, CoinPrice, WatchlistItem

User = get_user_model()

class WatchlistAPI(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(username="tester", password="testpass123")
        response = self.client.post("/api/token/",{
            "username": "tester",
            "password": "testpass123"
        })
        self.token = response.json()["access"]
        self.auth_header = f"Bearer {self.token}"

    def test_unauthenticated_access(self):
        response = self.client.get("/api/watchlist/")
        self.assertEqual(response.status_code, 401)

    def test_authenticated_access(self):
        response = self.client.get(
            "/api/watchlist/",
            HTTP_AUTHORIZATION=self.auth_header
        )
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
                coin__symbol="btc",
            ).count(),
            1
        )


    def test_watchlist_query_count(self):
        coin_one = Coin.objects.create(name="Bobrcoin", symbol="bobr")
        coin_two = Coin.objects.create(name="Tarcoin", symbol="bsg")
        WatchlistItem.objects.create(user=self.user, coin=coin_one)
        WatchlistItem.objects.create(user=self.user, coin=coin_two)

        with self.assertNumQueries(3):
            response = self.client.get(
                "/api/watchlist/",
                HTTP_AUTHORIZATION=self.auth_header
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

        user_b = User.objects.create_user(
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
        snapshot = Snapshot.objects.create(
            provider="test",
            total_coins=2,
            total_market_cap=150001.00
        )
        coin1 = Coin.objects.create(name="Babkacoin", symbol="bkc")
        coin2 = Coin.objects.create(name="MotoMoto", symbol="mot")

        CoinPrice.objects.create(
            coin=coin1,
            snapshot=snapshot,
            price=50001,
            volume_24h=1000004,
            change_24h=5.5
        )
        CoinPrice.objects.create(
            coin=coin2,
            snapshot=snapshot,
            price=102312,
            volume_24h=984322,
            change_24h=4.1
        )

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
        snapshot = Snapshot.objects.create(
            provider="test",
            total_coins=2,
            total_market_cap=100
        )
        ntc = Coin.objects.create(name="Nitcoin", symbol="ntc")
        pep = Coin.objects.create(name="Pepecoin", symbol="pep")

        CoinPrice.objects.create(
            coin=ntc,
            snapshot=snapshot,
            price=200,
            volume_24h=100,
            change_24h=5.0
        )
        CoinPrice.objects.create(
            coin=pep,
            snapshot=snapshot,
            price=300,
            volume_24h=500,
            change_24h=10.0
        )

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

    def test_coins_filter_price_range(self):
        snapshot = Snapshot.objects.create(provider="test", total_coins=2, total_market_cap=100000)
        ntc = Coin.objects.create(name="Nitcoin", symbol="ntc")
        pep = Coin.objects.create(name="Pepecoin", symbol="pep")

        CoinPrice.objects.create(coin=ntc, snapshot=snapshot, price=50000, volume_24h=1, change_24h=1)
        CoinPrice.objects.create(coin=pep, snapshot=snapshot, price=2, volume_24h=1, change_24h=1)

        response = self.client.get("/api/coins/?min_price=100")
        self.assertEqual(response.status_code, 200)
        results = response.json()
        if isinstance(results, list):
            self.assertEqual(len(results), 1)
            self.assertEqual(results[0]["symbol"], "ntc")
        else:
            self.assertEqual(len(results["results"]), 1)
            self.assertEqual(results["results"][0]["symbol"], "ntc")

        response = self.client.get("/api/coins/?max_price=50")
        self.assertEqual(response.status_code, 200)
        results = response.json()
        if isinstance(results, list):
            self.assertEqual(len(results), 1)
            self.assertEqual(results[0]["symbol"], "pep")
        else:
            self.assertEqual(len(results["results"]), 1)
            self.assertEqual(results["results"][0]["symbol"], "pep")

