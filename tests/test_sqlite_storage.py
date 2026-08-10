from storage.sqlite_storage import SqliteStorage

class TestSqliteStorage:

    def test_save_and_list_cadr(self):
        storage = SqliteStorage(db_path=":memory:")

        data = {
            "generated_at": "2026-07-15 11:30:00",
            "provider": "Test",
            "total_coins": 2,
            "total_market_cap": 1000001.0,
            "all_coins": [
                {"name": "Bitcoin", "symbol": "BTC", "price": 62000.0, "volume_24h": 35000000000.0, "24h_change": 2.5},
                {"name": "Ethereum", "symbol": "ETH", "price": 3400.0, "volume_24h": 15000000000.0, "24h_change": -1.2},
            ]
        }

        storage.save(data)

        cadr = storage.list_cadr()
        assert len(cadr) == 1
        assert cadr[0][2] == "Test"
        assert cadr[0][3] == 2
        assert cadr[0][4] == 1000001.0

    def test_compare_cadr(self):
        storage = SqliteStorage(db_path=":memory:")

        data1 = {
            "generated_at": "2026-07-15 11:30:00",
            "provider": "Test",
            "total_coins": 2,
            "total_market_cap": 1000001.0,
            "all_coins": [
                {"name": "Bitcoin", "symbol": "BTC", "price": 62000.0, "volume_24h": 35000000000.0, "24h_change": 2.5},
                {"name": "Ethereum", "symbol": "ETH", "price": 3400.0, "volume_24h": 15000000000.0, "24h_change": -1.2},
            ]
        }

        data2 = {
            "generated_at": "2026-07-15 11:30:00",
            "provider": "Test",
            "total_coins": 2,
            "total_market_cap": 1546669.0,
            "all_coins": [
                {"name": "Bitcoin", "symbol": "BTC", "price": 62001.0, "volume_24h": 35000000000.0, "24h_change": 0},
                {"name": "Ethereum", "symbol": "ETH", "price": 2100.0, "volume_24h": 15000000000.0, "24h_change": 0},
            ]
        }

        storage.save(data1)
        storage.save(data2)

        rows = storage.compare_cadr(1, 2)

        assert len(rows) == 2

        btc_row = [i for i in rows if i[0] == "BTC"][0]
        assert btc_row[3] == 1

        eth_row = [i for i in rows if i[0] == "ETH"][0]
        assert eth_row[3] == -1300