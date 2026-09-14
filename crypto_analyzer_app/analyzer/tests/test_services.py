from django.test import TestCase
from unittest.mock import patch, Mock

from django.contrib.auth import get_user_model

from analyzer.services import validate_symbol, add_to_watchlist, remove_from_watchlist
from analyzer.models import Coin, WatchlistItem

import requests

User = get_user_model()


class ValidateSymbolTests(TestCase):

    @patch("analyzer.services.requests.Session.get")
    def test_get_validate_symbol(self, mock_get):
        mock_response = Mock()
        mock_response.json.return_value = {"coins": [{"symbol": "btc", "name": "Bitcoin"}]}
        mock_get.return_value = mock_response
        temp = validate_symbol("btc")
        self.assertEqual(temp, {"valid": True, "name": "Bitcoin"})
        mock_get.assert_called_once_with("https://api.coingecko.com/api/v3/search?query=btc")

    @patch("analyzer.services.requests.Session.get")
    def test_validate_symbol_invalid(self, mock_get):
        mock_response = Mock()
        mock_response.json.return_value = {"coins": []}
        mock_get.return_value = mock_response
        temp = validate_symbol("ttv")
        self.assertFalse(temp)
        mock_get.assert_called_once_with("https://api.coingecko.com/api/v3/search?query=ttv")


class WatchlistTests(TestCase):

    def test_add_to_watchlist_success(self):
        user = User.objects.create_user(
            username="tester",
            password="321",
        )
        coin_data = {
            "valid": True,
            "name": "Bitcoin",
        }
        result = add_to_watchlist(
            user=user,
            symbol="btc",
            coin_data=coin_data,
        )

        self.assertEqual(result.user, user)
        self.assertEqual(result.coin.symbol, "BTC")
        self.assertEqual(result.coin.name, "Bitcoin")

    def test_remove_from_watchlist_success(self):
        user = User.objects.create_user(username="tester", password="321")
        coin = Coin.objects.create(name="Bitcoin", symbol="BTC")
        WatchlistItem.objects.create(user=user, coin=coin)
        result = remove_from_watchlist(user, "BTC")
        self.assertEqual(result, {"valid": True, "message": "Данные успешно удалены"})

    def test_coin_endpoint_is_read_only(self):
        response = self.client.post(
            "/api/coins/",
            {
                "name": "Bitcoin",
                "symbol": "BTC",
            },
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 405)

    def test_snapshot_endpoint_is_read_only(self):
        response = self.client.post(
            "/api/snapshots/",
            {
                "provider": "test",
                "total_coins": 1,
                "total_market_cap": "100.00",
            },
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 405)
