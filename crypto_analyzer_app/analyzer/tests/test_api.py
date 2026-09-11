from django.test import TestCase
from django.contrib.auth import get_user_model
from analyzer.models import Coin, WatchlistItem

from unittest.mock import patch

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

    @patch("analyzer.serializer.service_validate_symbol")
    def test_user_isolation(self, mock_validate):
        mock_validate.return_value = {
            "valid": True,
            "name": "Bitcoin",
        }

        # User A добавляет BTC
        response = self.client.post(
            "/api/watchlist/",
            {"symbol": "btc"},
            content_type="application/json",
            HTTP_AUTHORIZATION=self.auth_header,
        )

        self.assertEqual(response.status_code, 201)

        # Создаём User B
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

        # User B получает свой watchlist
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