import pytest
from dataclasses import replace

from storage.sqlite_storage import SqliteStorage


def coin_to_dict(coin):
    return {
        "name": coin.name,
        "symbol": coin.symbol,
        "price": coin.current_price,
        "volume_24h": coin.total_volume,
        "24h_change": coin.price_change_for_24h,
    }


def make_data(coins, generated_at, total_market_cap):
    return {
        "generated_at": generated_at,
        "provider": "Test",
        "total_coins": len(coins),
        "total_market_cap": total_market_cap,
        "all_coins": [coin_to_dict(coin) for coin in coins],
    }


class TestSqliteStorage:

    def test_save_and_list_cadr(self, bitcoin, ethereum):
        storage = SqliteStorage(db_path=":memory:")

        data = make_data(
            [bitcoin, ethereum],
            "2026-07-15 11:30:00",
            1000001.0,
        )

        storage.save(data)

        cadr = storage.list_cadr()

        assert len(cadr) == 1
        assert cadr[0][2] == "Test"
        assert cadr[0][3] == 2
        assert cadr[0][4] == 1000001.0

    def test_compare_cadr(self, bitcoin, ethereum):
        storage = SqliteStorage(db_path=":memory:")

        data1 = make_data(
            [bitcoin, ethereum],
            "2026-07-15 11:30:00",
            1000001.0,
        )

        bitcoin_new = replace(bitcoin, current_price=62001.0)
        ethereum_new = replace(ethereum, current_price=2100.0)

        data2 = make_data(
            [bitcoin_new, ethereum_new],
            "2026-07-15 12:30:00",
            1546669.0,
        )

        storage.save(data1)
        storage.save(data2)

        rows = storage.compare_cadr(1, 2)

        assert len(rows) == 2

        btc_row = [row for row in rows if row[0] == "BTC"][0]
        assert btc_row[3] == 1

        eth_row = [row for row in rows if row[0] == "ETH"][0]
        assert eth_row[3] == -1300

    def test_compare_cadr_skips_null_prices(self, bitcoin, ethereum):
        storage = SqliteStorage(db_path=":memory:")

        ethereum_without_price = replace(
            ethereum,
            current_price=None,
        )

        data1 = make_data(
            [bitcoin, ethereum_without_price],
            "2026-07-15 11:30:00",
            1000001.0,
        )

        bitcoin_new = replace(
            bitcoin,
            current_price=63000.0,
        )
        ethereum_new = replace(
            ethereum,
            current_price=3500.0,
        )

        data2 = make_data(
            [bitcoin_new, ethereum_new],
            "2026-07-15 12:30:00",
            1100000.0,
        )

        storage.save(data1)
        storage.save(data2)

        rows = storage.compare_cadr(1, 2)

        symbols = {row[0] for row in rows}

        assert "BTC" in symbols
        assert "ETH" not in symbols

    def test_compare_cadr_with_duplicate_symbol(
            self,
            bitcoin,
            ethereum,
    ):
        storage = SqliteStorage(db_path=":memory:")

        bitcoin_duplicate = replace(
            bitcoin,
            current_price=61000.0,
        )

        data1 = make_data(
            [bitcoin, bitcoin_duplicate, ethereum],
            "2026-07-15 11:30:00",
            1000001.0,
        )

        bitcoin_new = replace(
            bitcoin,
            current_price=62001.0,
        )
        ethereum_new = replace(
            ethereum,
            current_price=2100.0,
        )

        data2 = make_data(
            [bitcoin_new, ethereum_new],
            "2026-07-15 12:30:00",
            1546669.0,
        )

        storage.save(data1)
        storage.save(data2)

        rows = storage.compare_cadr(1, 2)

        assert len(rows) == 2
        assert {row[0] for row in rows} == {"BTC", "ETH"}

    def test_get_coin_history(self, bitcoin):
        storage = SqliteStorage(db_path=":memory:")

        data1 = make_data(
            [bitcoin],
            "2026-07-15 11:30:00",
            1000001.0,
        )

        bitcoin_new = replace(
            bitcoin,
            current_price=62001.0,
        )

        data2 = make_data(
            [bitcoin_new],
            "2026-07-15 12:30:00",
            1100000.0,
        )

        storage.save(data1)
        storage.save(data2)

        history = storage.get_coin_history("BTC")

        assert len(history) == 2
        assert history[0][0] == "2026-07-15 11:30:00"
        assert history[0][1] == bitcoin.current_price
        assert history[1][0] == "2026-07-15 12:30:00"
        assert history[1][1] == 62001.0

    def test_get_top_gainers_and_losers_last(self, bitcoin, ethereum):
        storage = SqliteStorage(db_path=":memory:")

        bitcoin_new = replace(
            bitcoin,
            current_price=62001.0,
            price_change_for_24h=5.5,
        )
        ethereum_new = replace(
            ethereum,
            current_price=2100.0,
            price_change_for_24h=-3.2,
        )

        data = make_data(
            [bitcoin_new, ethereum_new],
            "2026-07-15 12:30:00",
            1546669.0,
        )

        storage.save(data)

        gainers = storage.get_top_gainers_last(limit=1)
        losers = storage.get_top_loser_last(limit=1)

        assert len(gainers) == 1
        assert gainers[0][1] == "BTC"
        assert gainers[0][3] == 5.5

        assert len(losers) == 1
        assert losers[0][1] == "ETH"
        assert losers[0][3] == -3.2

    def test_get_top_last_invalid_direction(self):
        storage = SqliteStorage(db_path=":memory:")

        with pytest.raises(
                ValueError,
                match="Некорректное направление сортировки",
        ):
            storage._get_top_last(limit=5, direction="INVALID")