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

class TestCoinString:
    def test_str_all_stat(self, tomasikshcelbek):
        result = str(tomasikshcelbek)
        assert "Tomasik" in result
        assert "TMS" in result
        assert "$1,400.00" in result
        assert "-13.80%" in result

    def test_str_min_stat(self):
        coin = Coin(name="Tester", symbol="TSR")
        result = str(coin)
        assert "Tester" in result
        assert "TSR" in result
        assert "Данные отсутствуют" in result

class TestCoinRepr:
    def test_repr_to_change(self, tomasikshcelbek):
        result = repr(tomasikshcelbek)
        assert "Coin(TMS:" in result
        assert "-13.80%" in result

    def test_repr_not_change(self, tarcoin):
        result = repr(tarcoin)
        assert "Coin(EFT:" in result
        assert "Данные отсутствуют" in result

class TestCoinComparison:
    def test_lt_true(self, ethereum, bitcoin):
        assert ethereum < bitcoin

    def test_lt_false(self, bitcoin, ethereum):
        assert not (bitcoin < ethereum)

    def test_gt_true(self, bitcoin, ethereum):
        assert bitcoin > ethereum

    def test_gt_false(self, ethereum, bitcoin):
        assert not (ethereum > bitcoin)

    def test_compare(self, bitcoin, ethereum):
        assert bitcoin > ethereum

    def test_compare_rev(self, ethereum, tarcoin):
        assert ethereum < tarcoin

class TestMarketCap:
    def test_market_cap_true(self, ethereum, bitcoin):
        assert ethereum.compare_by_market_cap(bitcoin)

    def test_market_cap_false(self, bitcoin, ethereum):
        assert not bitcoin.compare_by_market_cap(ethereum)