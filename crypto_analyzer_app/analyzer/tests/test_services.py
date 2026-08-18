from unittest.mock import Mock, patch

import requests
from django.contrib.auth import get_user_model
from django.test import TestCase

from analyzer.models import Coin, CoinPrice, Snapshot, WatchlistItem
from analyzer.services import add_to_watchlist, remove_from_watchlist, validate_symbol
from analyzer.tasks import fetch_snapshot_task

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
    @patch("analyzer.services.validate_symbol")
    def test_add_to_watchlist_success(self, mock_validate):
        mock_validate.return_value = {"valid": True, "name": "Bitcoin"}
        user = User.objects.create_user(username="tester", password="321")
        result = add_to_watchlist(user, "btc")
        self.assertEqual(result.coin.symbol, "btc")
        mock_validate.assert_called_once_with("btc")

    def test_remove_from_watchlist_success(self):
        user = User.objects.create_user(username="tester", password="321")
        coin = Coin.objects.create(name="Bitcoin", symbol="btc")
        WatchlistItem.objects.create(user=user, coin=coin)
        result = remove_from_watchlist(user, "btc")
        self.assertEqual(result, {"valid": True, "message": "Данные успешно удалены"})


class CeleryTasksTests(TestCase):
    @patch("analyzer.tasks._fetch_data")
    def test_success(self, mock_fetch):
        mock_fetch.return_value = [
            {"name": "Bibicoin", "symbol": "bbc", "current_price": 50000, "total_volume": 100, "price_change_percentage_24h": 5}
        ]
        result = fetch_snapshot_task.run("coingecko", 3)

        self.assertEqual(result["snapshot_id"], Snapshot.objects.last().id)
        self.assertEqual(Snapshot.objects.count(), 1)
        self.assertEqual(CoinPrice.objects.count(), 1)

        mock_fetch.assert_called_once_with("coingecko", 3)

        coin = CoinPrice.objects.first()
        self.assertEqual(coin.coin.symbol, "bbc")
        self.assertEqual(coin.price, 50000)

    @patch("analyzer.tasks._fetch_data")
    def test_retry_on_conn_error(self, mock_fetch):
        mock_fetch.side_effect = requests.exceptions.ConnectionError("Нет соединения")
        try:
            fetch_snapshot_task.run("coingecko", 3)
            self.fail("Должна была бросить ошибку")
        except requests.exceptions.ConnectionError:
            pass

        self.assertEqual(Snapshot.objects.count(), 0)
        self.assertEqual(CoinPrice.objects.count(), 0)
        mock_fetch.assert_called_once_with("coingecko", 3)

    @patch("analyzer.tasks._fetch_data")
    def test_idempotency(self, mock_fetch):
        mock_fetch.return_value = [
            {"name": "Bibcoin", "symbol": "bbc", "current_price": 50000, "total_volume": 100, "price_change_percentage_24h": 5}
        ]

        result1 = fetch_snapshot_task.run("coingecko", 3)
        result2 = fetch_snapshot_task.run("coingecko", 3)
        self.assertEqual(result1["snapshot_id"], result2["snapshot_id"])
        self.assertTrue(result2.get("already_exists"))

        self.assertEqual(Snapshot.objects.count(), 1)
        self.assertEqual(CoinPrice.objects.count(), 1)

    @patch("analyzer.tasks._fetch_data")
    def test_multiple_coins(self, mock_fetch):
        mock_fetch.return_value = [
            {"name": "Bibcoin", "symbol": "bbc", "current_price": 50000, "total_volume": 100, "price_change_percentage_24h": 5},
            {"name": "Ethereum", "symbol": "eth", "current_price": 3000, "total_volume": 200, "price_change_percentage_24h": -2},
        ]
        result = fetch_snapshot_task.run("coingecko", 2)

        self.assertEqual(result["snapshot_id"], Snapshot.objects.last().id)
        self.assertEqual(CoinPrice.objects.count(), 2)
        self.assertEqual(Snapshot.objects.count(), 1)

        bbc_price = CoinPrice.objects.get(coin__symbol="bbc")
        self.assertEqual(bbc_price.price, 50000)

        eth_price = CoinPrice.objects.get(coin__symbol="eth")
        self.assertEqual(eth_price.price, 3000)
        self.assertEqual(bbc_price.coin.name, "Bibcoin")
