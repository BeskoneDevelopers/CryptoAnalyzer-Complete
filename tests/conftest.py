from models.coin import Coin

import pytest


@pytest.fixture
def bitcoin():
    return Coin(
        name="Bitcoin",
        symbol="BTC",
        current_price=62000.0,
        total_volume=35000000000.0,
        market_cap=1200000000000.0,
        price_change_for_24h=2.0
    )

@pytest.fixture
def ethereum():
    return Coin(
        name="Ethereum",
        symbol="ETH",
        current_price=3400.0,
        total_volume=15000000000.0,
        market_cap=400000000000.0,
        price_change_for_24h=-1.1
    )

@pytest.fixture
def bobrecoin():
    return Coin(
        name="Bobrcoin",
        symbol="BRC",
        current_price=54300.0,
        total_volume=14000000000.0,
        market_cap=432000000000.0,
        price_change_for_24h=16.5
    )

@pytest.fixture
def tomasikshcelbek():
    return Coin(
        name="Tomasik",
        symbol="TMS",
        current_price=1400.0,
        total_volume=6000000000.0,
        market_cap=2300000000.0,
        price_change_for_24h=-13.8
    )

@pytest.fixture
def tarcoin():
    return Coin(
        name="Tarcoin",
        symbol="EFT",
        current_price=100.0,
        total_volume=20000000.0,
        market_cap=7000000000.0,
        price_change_for_24h=None
    )

@pytest.fixture
def sample_coins(bitcoin, bobrecoin, tarcoin, tomasikshcelbek, ethereum):
    return [bitcoin, bobrecoin, tarcoin, tomasikshcelbek, ethereum]


###################### Подключение mock тестов для coingecko ##################

@pytest.fixture
def mock_coingecko_response():
    return [
        {
            "name": "Bitcoin",
            "symbol": "btc",
            "current_price": 62000.0,
            "total_volume": 35000000000.0,
            "market_cap": 1200000000000.0,
            "price_change_percentage_24h": 2.5
        },
        {
            "name": "Ethereum",
            "symbol": "eth",
            "current_price": 3400.0,
            "total_volume": 15000000000.0,
            "market_cap": 400000000000.0,
            "price_change_percentage_24h": -1.2
        },
        {
            "name": "Bobrcoin",
            "symbol": "brc",
            "current_price": 54300.0,
            "total_volume": 14000000000.0,
            "market_cap": 432000000000.0,
            "price_change_percentage_24h": 16.5
        }
    ]

###################### Подключение mock тестов для coinmarket ##################

@pytest.fixture
def mock_coinmarket_response():
    return {
        "data": [
            {
                "name": "Bitcoin",
                "symbol": "BTC",
                "quote": {
                    "USD": {
                        "price": 62000.0,
                        "volume_24h": 35000000000.0,
                        "market_cap": 1200000000000.0,
                        "percent_change_24h": 2.5
                    }
                }
            },
            {
                "name": "Ethereum",
                "symbol": "ETH",
                "quote": {
                    "USD": {
                        "price": 3400.0,
                        "volume_24h": 15000000000.0,
                        "market_cap": 400000000000.0,
                        "percent_change_24h": -1.2
                    }
                }
            }
        ]
    }
