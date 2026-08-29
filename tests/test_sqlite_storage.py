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