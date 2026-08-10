import requests_mock
import pytest

from requests.exceptions import HTTPError

from providers.coingecko import CoinGeckoProvider
from providers.coinmarketcap import CoinMarketCapProvider

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
        call_count = [0]

        def flaky_response(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] < 3:
                raise ConnectionError("Temporary failure")
            return mock_coingecko_response

        with requests_mock.Mocker() as mock:
            mock.get(CoinGeckoProvider.URL_API, json=flaky_response)
            coins = provider.fetch_top_coins(limit=3)

        assert call_count[0] == 3
        assert len(coins) == 3


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



