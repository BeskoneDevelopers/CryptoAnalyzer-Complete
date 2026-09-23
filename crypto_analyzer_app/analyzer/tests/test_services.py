from unittest.mock import Mock, patch

import pytest
import requests
from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase

from analyzer.models import Coin, CoinPrice, Snapshot, WatchlistItem
from analyzer.services import (
    ANALYTICS_CACHE_TTL,
    add_to_watchlist,
    get_or_set_cache,
    refresh_analytics_cache,
    remove_from_watchlist,
    validate_symbol,
)
from analyzer.tasks import _get_retry_countdown

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
        result = remove_from_watchlist(user, "btc")
        self.assertEqual(result, {"valid": True, "message": "Данные успешно удалены"})

    def test_coin_endpoint_is_read_only(self):
        response = self.client.post(
            "/api/v1/coins/",
            {
                "name": "Bitcoin",
                "symbol": "BTC",
            },
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 401)

    def test_snapshot_endpoint_is_read_only(self):
        coin = Coin.objects.create(
            name="Bitcoin",
            symbol="BTC",
        )

        snapshot = Snapshot.objects.create(
            provider="test",
            total_coins=1,
            total_market_cap="100.00",
        )

        CoinPrice.objects.create(
            coin=coin,
            snapshot=snapshot,
            price="50.00",
            volume_24h="1000.00",
            change_24h="1.50",
            market_cap="5000.00",
        )

        get_response = self.client.get("/api/v1/snapshots/")
        self.assertEqual(get_response.status_code, 200)

        post_response = self.client.post(
            "/api/v1/snapshots/",
            {
                "provider": "test",
                "total_coins": 1,
                "total_market_cap": "100.00",
            },
            content_type="application/json",
        )

        self.assertEqual(post_response.status_code, 401)


class CeleryTasksTests(TestCase):
    @patch("analyzer.tasks._fetch_data")
    def test_success(self, mock_fetch):
        from analyzer.tasks import fetch_snapshot_task

        mock_fetch.return_value = [
            {
                "name": "Bibicoin",
                "symbol": "bbc",
                "current_price": 50000,
                "total_volume": 100,
                "price_change_percentage_24h": 5,
                "market_cap": 250000,
            }
        ]

        result = fetch_snapshot_task.run("coingecko", 3)

        self.assertEqual(result["snapshot_id"], Snapshot.objects.first().id)
        self.assertEqual(Snapshot.objects.count(), 1)

        snapshot = Snapshot.objects.first()
        self.assertEqual(snapshot.total_market_cap, 250000)

        self.assertEqual(CoinPrice.objects.count(), 1)

        mock_fetch.assert_called_once_with("coingecko", 3)

        coin = CoinPrice.objects.first()
        self.assertEqual(coin.coin.symbol, "bbc")
        self.assertEqual(coin.price, 50000)

    @patch("analyzer.tasks._fetch_data")
    def test_retry_on_conn_error(self, mock_fetch):
        from analyzer.tasks import fetch_snapshot_task

        mock_fetch.side_effect = requests.exceptions.ConnectionError("Нет соединения")

        result = fetch_snapshot_task.apply(args=("coingecko", 3))

        self.assertTrue(result.failed())
        self.assertEqual(Snapshot.objects.count(), 0)
        self.assertEqual(CoinPrice.objects.count(), 0)
        self.assertEqual(mock_fetch.call_count, 4)

    @patch("analyzer.tasks._fetch_data")
    def test_idempotency(self, mock_fetch):
        from analyzer.tasks import fetch_snapshot_task

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
        from analyzer.tasks import fetch_snapshot_task

        mock_fetch.return_value = [
            {"name": "Bibcoin", "symbol": "bbc", "current_price": 50000, "total_volume": 100, "price_change_percentage_24h": 5},
            {"name": "Ethereum", "symbol": "eth", "current_price": 3000, "total_volume": 200, "price_change_percentage_24h": -2},
        ]
        result = fetch_snapshot_task.run("coingecko", 2)

        self.assertEqual(result["snapshot_id"], Snapshot.objects.first().id)
        self.assertEqual(CoinPrice.objects.count(), 2)
        self.assertEqual(Snapshot.objects.count(), 1)

        bbc_price = CoinPrice.objects.get(coin__symbol="bbc")
        self.assertEqual(bbc_price.price, 50000)

        eth_price = CoinPrice.objects.get(coin__symbol="eth")
        self.assertEqual(eth_price.price, 3000)
        self.assertEqual(bbc_price.coin.name, "Bibcoin")

    def test_retry_countdown_backoff(self):
        self.assertEqual(_get_retry_countdown(0), 60)
        self.assertEqual(_get_retry_countdown(1), 120)
        self.assertEqual(_get_retry_countdown(2), 240)
        self.assertEqual(_get_retry_countdown(3), 300)

    @patch("analyzer.tasks.refresh_analytics_cache")
    @patch("analyzer.tasks._fetch_data")
    def test_does_not_refresh_cache_for_existing_snapshot(
        self,
        mock_fetch,
        mock_refresh_cache,
    ):
        from analyzer.tasks import fetch_snapshot_task

        mock_fetch.return_value = [
            {
                "name": "Bitcoin",
                "symbol": "btc",
                "current_price": 50000,
                "total_volume": 100,
                "price_change_percentage_24h": 5,
            }
        ]

        fetch_snapshot_task.run("coingecko", 1)

        mock_refresh_cache.reset_mock()

        fetch_snapshot_task.run("coingecko", 1)

        mock_refresh_cache.assert_not_called()

    @patch("analyzer.tasks.refresh_analytics_cache")
    @patch("analyzer.tasks._fetch_data")
    def test_refresh_cache_after_snapshot_created(
        self,
        mock_fetch,
        mock_refresh_cache,
    ):
        from analyzer.tasks import fetch_snapshot_task

        mock_fetch.return_value = [
            {
                "name": "Bitcoin",
                "symbol": "btc",
                "current_price": 50000,
                "total_volume": 100,
                "price_change_percentage_24h": 5,
            }
        ]

        fetch_snapshot_task.run("coingecko", 1)

        mock_refresh_cache.assert_called_once_with()

    def test_fetch_snapshot_unknown_provider(self):
        from analyzer.tasks import fetch_snapshot_task

        with pytest.raises(ValueError, match="Неизвестный провайдер"):
            fetch_snapshot_task.run(provider="test")

    def test_coinmarketcap_without_api_key(self):
        from analyzer.tasks import fetch_snapshot_task

        with patch("analyzer.tasks.settings.CMC_API_KEY", None):
            with self.assertRaisesRegex(ValueError, "Отсутствует API ключ"):
                fetch_snapshot_task.run(provider="coinmarketcap")


class CacheServiceTests(SimpleTestCase):
    @patch("analyzer.services.cache")
    def test_get_or_set_cache_miss(self, mock_cache):
        mock_cache.get.return_value = None

        loader = Mock(return_value={"value": 123})

        result = get_or_set_cache("test_key", loader)

        self.assertEqual(result, {"value": 123})
        loader.assert_called_once_with()
        mock_cache.get.assert_called_once_with("test_key")
        mock_cache.set.assert_called_once_with(
            "test_key",
            {"value": 123},
            ANALYTICS_CACHE_TTL,
        )

    @patch("analyzer.services.cache")
    def test_get_or_set_cache_hit(self, mock_cache):
        cached_data = {"value": 123}
        mock_cache.get.return_value = cached_data

        loader = Mock()

        result = get_or_set_cache("test_key", loader)

        self.assertEqual(result, cached_data)
        mock_cache.get.assert_called_once_with("test_key")
        loader.assert_not_called()
        mock_cache.set.assert_not_called()

    @patch("analyzer.services.cache")
    def test_get_or_set_cache_force_refresh(self, mock_cache):
        fresh_data = {"value": 999}
        loader = Mock(return_value=fresh_data)

        result = get_or_set_cache(
            "test_key",
            loader,
            force_refresh=True,
        )

        self.assertEqual(result, fresh_data)
        mock_cache.get.assert_not_called()
        loader.assert_called_once_with()
        mock_cache.set.assert_called_once_with(
            "test_key",
            fresh_data,
            ANALYTICS_CACHE_TTL,
        )

    @patch("analyzer.services.cache")
    def test_get_or_set_cache_does_not_cache_error(self, mock_cache):
        mock_cache.get.return_value = None

        error = {"error": "Снимков нет!"}
        loader = Mock(return_value=error)

        result = get_or_set_cache("test_key", loader)

        self.assertEqual(result, error)
        loader.assert_called_once_with()
        mock_cache.set.assert_not_called()

    @patch("analyzer.services.get_cached_top_volume")
    @patch("analyzer.services.get_cached_top_movers")
    @patch("analyzer.services.get_cached_market_stats")
    def test_refresh_analytics_cache_forces_refresh(
        self,
        mock_market_stats,
        mock_top_movers,
        mock_top_volume,
    ):
        refresh_analytics_cache()

        mock_market_stats.assert_called_once_with(force_refresh=True)
        mock_top_movers.assert_called_once_with(force_refresh=True)
        mock_top_volume.assert_called_once_with(force_refresh=True)
