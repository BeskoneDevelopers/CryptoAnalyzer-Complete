from models.portfolio import CryptoPortfolio

class TestPortfolioCreation:
    def test_empty_portfolio(self):
        portfolio = CryptoPortfolio()
        assert len(portfolio) == 0

    def test_portfolio_semple_coins(self, sample_coins):
        portfolio = CryptoPortfolio(sample_coins)
        assert len(portfolio) == 5

    def test_coin_returns_copy(self, tarcoin):
        portfolio = CryptoPortfolio([tarcoin])
        coin_copy = portfolio.coins
        coin_copy.clear()
        assert len(portfolio) == 1

    def test_top_gainers(self, sample_coins):
        portfolio = CryptoPortfolio(sample_coins)
        gainers = portfolio.get_top_gainers(3)
        assert len(gainers) == 3
        assert gainers[0].symbol == "BRC"

    def test_top_losers(self, sample_coins):
        portfolio = CryptoPortfolio(sample_coins)
        losers = portfolio.get_top_losers(3)
        assert len(losers) == 3
        assert losers[0].symbol == "TMS"

    def test_highest_volume(self, sample_coins):
        portfolio = CryptoPortfolio(sample_coins)
        highest = portfolio.get_highest_volume()
        assert highest.symbol == "BTC"

    def test_empty_portfolio_analysis(self):
        portfolio = CryptoPortfolio()

        assert portfolio.get_top_losers() == []
        assert portfolio.get_top_losers() == []
        assert portfolio.get_highest_volume() == None
        assert portfolio.get_total_market_cap() == 0