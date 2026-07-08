import pytest

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
    @pytest.mark.parametrize("fixture_name, expected_in_str", [
        ("bitcoin", ["Bitcoin", "BTC", "62,000.00", "+2.00%"]),
        ("tomasikshcelbek", ["Tomasik", "TMS", "1,400.00", "-13.80%"]),
        ("tarcoin", ["Tarcoin", "EFT", "100.00", "Данные отсутствуют"])
    ])
    def test_str_contains(self, fixture_name, expected_in_str, request):
        coin = request.getfixturevalue(fixture_name)
        result = str(coin)
        for part in expected_in_str:
            assert part in result, f"Ожидание - '{part}' / Ответ - '{result}'"


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
    @pytest.mark.parametrize("coin_name_1,coin_name_2,exp_lt,exp_gt", [
        ("ethereum", "bitcoin", True, False),
        ("bitcoin", "ethereum", False, True),
        ("bitcoin", "tarcoin", False, True),
        ("tarcoin", "ethereum", False, True),
    ])
    def test_comparison(self, coin_name_1, coin_name_2, exp_lt, exp_gt, request):
        coin1 = request.getfixturevalue(coin_name_1)
        coin2 = request.getfixturevalue(coin_name_2)

        assert (coin1 < coin2) == exp_lt
        assert (coin1 > coin2) == exp_gt


class TestMarketCap:
    def test_market_cap_true(self, ethereum, bitcoin):
        assert ethereum.compare_by_market_cap(bitcoin)

    def test_market_cap_false(self, bitcoin, ethereum):
        assert not bitcoin.compare_by_market_cap(ethereum)