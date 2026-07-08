from models.coin import Coin

class TestCoinCreated:
    def test_created_coin_all_stat(self):
        coin = Coin(
        name="Tomasik",
        symbol="TMS",
        current_price=1400.0,
        total_volume=6000000000.0,
        market_cap=2300000000.0,
        price_change_for_24h=-13.8
        )
        assert coin.name == "Tomasik"
        assert coin.symbol == "TMS"
        assert coin.current_price == 1400.0
        assert coin.total_volume == 6000000000.0
        assert coin.market_cap == 2300000000.0
        assert coin.price_change_for_24h == -13.8

    def test_created_coin_min_stat(self):
        coin = Coin(
            name="Tester",
            symbol="TSR"
        )

        assert coin.name == "Tester"
        assert coin.symbol  == "TSR"
        assert coin.current_price is None
        assert coin.total_volume is None
        assert coin.market_cap is None
        assert coin.price_change_for_24h is None