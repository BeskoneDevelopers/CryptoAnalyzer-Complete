from django.test import TestCase
from django.contrib.auth import get_user_model
from django.db import reset_queries
from analyzer.models import Coin

from unittest.mock import patch

from analyzer.models import WatchlistItem

from analyzer.models import Snapshot, CoinPrice

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

    @patch("analyzer.serializer.validate_symbol")
    def test_add_to_watchlist(self, mock_validate):
        mock_validate.return_value = {"valid": True, "name": "Bitcoin"}

        response = self.client.post(
            "/api/watchlist/",
            {"symbol": "btc"},
            content_type="application/json",
            HTTP_AUTHORIZATION=self.auth_header
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["coin"], "Bitcoin")

    def test_watchlist_query_count(self):
        coin_one = Coin.objects.create(name="Bobrcoin", symbol="bobr")
        coin_two = Coin.objects.create(name="Tarcoin", symbol="bsg")
        WatchlistItem.objects.create(user=self.user, coin=coin_one)
        WatchlistItem.objects.create(user=self.user, coin=coin_two)

        reset_queries()

        with self.assertNumQueries(2):
            response = self.client.get(
                "/api/watchlist/",
                HTTP_AUTHORIZATION=self.auth_header
            )

        self.assertEqual(response.status_code, 200)

    class AnalyticsAPITest(TestCase):

        def setUp(self):
            self.user = User.objects.create_user(username="tester", password="testpass123")

        def test_market_stats_structure(self):
            snapshot = Snapshot.objects.create(
                privider="test",
                total_coins=2,
                total_market_cap=150001.00
            )
            coin = Coin.objects.create(name="Babkacoin", symbol="bkc")
            CoinPrice.objects.create(
                coin=coin,
                snapshot=snapshot,
                price=50001,
                volume_24h=1000004,
                change_24h=5.5)
            response = self.client.get("/api/analytics/market-stats/")
            self.assertEqual(response.status_code, 200)

            data = response.json()
            self.assertEqual(data["snapshot_id"], snapshot.id)
            self.assertEqual(data["provider"], "test")
            self.assertEqual(data["min_price"], "50001.00000000")
            self.assertEqual(data["max_price"], "50001.00000000")
            self.assertEqual(data["total_market_cap"], "150001.00000000")

        def test_market_stats(self):
            response = self.client.get("/api/analytics/market-stats/")
            self.assertEqual(response.status_code, 404)
            self.assertEqual("error", response.json())


