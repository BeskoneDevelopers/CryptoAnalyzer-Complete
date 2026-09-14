import requests.exceptions
import requests_mock
import pytest

from requests.exceptions import HTTPError
from unittest.mock import patch

from providers.coingecko import CoinGeckoProvider
from providers.coinmarketcap import CoinMarketCapProvider
from providers import get_provider

class TestCoinGeckoProvider:
    def test_top_coins_return(self, mock_coingecko_response):
        provider = CoinGeckoProvider()

        with requests_mock.Mocker() as mock:
            mock.get(
                CoinGeckoProvider.URL_API,
                json=mock_coingecko_response
            )
            coins = provider.fetch_top_coins(limit=3)

        assert len(coins) == 3
        assert coins[0].name == "Bitcoin"
        assert coins[0].symbol == "BTC"
        assert coins[0].price_change_for_24h == 2.5

    def test_top_coins_error(self):
        provider = CoinGeckoProvider()

        with requests_mock.Mocker() as mock:
            mock.get(
                CoinGeckoProvider.URL_API,
                status_code=500
            )
            with pytest.raises(HTTPError):
                provider.fetch_top_coins()

    def test_retry_decorator(self, mock_coingecko_response):
        provider = CoinGeckoProvider()

        responses = [
            {
                "exc": requests.exceptions.ConnectionError(
                    "Temporary failure"
                )
            },
            {
                "exc": requests.exceptions.ConnectionError(
                    "Temporary failure"
                )
            },
            {
                "json": mock_coingecko_response
            }
        ]
        with requests_mock.Mocker() as mock:
            mock.get(
                CoinGeckoProvider.URL_API,
                response_list=responses,
            )
            coins = provider.fetch_top_coins(limit=3)

        assert mock.call_count == 3
        assert len(coins) == 3

    def test_retry_raises_after_max_attempts(self):
        provider = CoinGeckoProvider()

        with requests_mock.Mocker() as mock:
            mock.get(
                CoinGeckoProvider.URL_API,
                response_list=[
                    {"exc": requests.exceptions.ConnectionError("Temporary failure")},
                    {"exc": requests.exceptions.ConnectionError("Temporary failure")},
                    {"exc": requests.exceptions.ConnectionError("Temporary failure")},
                ]
            )

            with patch("providers.coingecko.time.sleep") as mock_sleep:
                with pytest.raises(requests.exceptions.ConnectionError):
                    provider.fetch_top_coins(limit=3)

        assert mock.call_count == 3
        assert mock_sleep.call_count == 2


class TestCoinMarketProvider:
    def test_fetch_top_coins(self, mock_coinmarket_response, monkeypatch):
        monkeypatch.setenv("API_KEY", "ugi_vugi")

        provider = CoinMarketCapProvider()

        with requests_mock.Mocker() as mock:
            mock.get(
                CoinMarketCapProvider.URL_API,
                json=mock_coinmarket_response
            )
            coins = provider.fetch_top_coins(limit=2)

        assert len(coins) == 2
        assert coins[0].name == "Bitcoin"
        assert coins[0].symbol == "BTC"
        assert coins[0].price_change_for_24h == 2.5
        assert coins[0].market_cap == 1200000000000.0

    def test_init_without_api_key(self, monkeypatch):
        monkeypatch.delenv("API_KEY", raising=False)

        with pytest.raises(ValueError, match="ключ не найден"):
            CoinMarketCapProvider()

class TestProviders:
    def test_get_provider_unknown_provider(self):
        with pytest.raises(ValueError):
            get_provider("unknown")



