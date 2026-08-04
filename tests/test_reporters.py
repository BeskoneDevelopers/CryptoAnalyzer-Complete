from models import CryptoPortfolio

from reporters import JsonReporter, CsvReporter, ConsoleReporter


import json

from io import StringIO
from rich.console import Console


class TestJsonReporter:

    def test_json_reporter(self, sample_coins, tmp_path):
        filepath = tmp_path / "test_mega_report.json"
        reporter = JsonReporter(filename=str(filepath))

        portfolio = CryptoPortfolio(sample_coins)
        reporter.report(portfolio, "TestJsonProvider", top_count=3)

        assert filepath.exists()

        with open(filepath) as f:
            data = json.load(f)

        assert data["total_coins"] == 5
        assert data["provider"] == "TestJsonProvider"

        assert len(data["top_gainers"]) == 3
        assert data["top_gainers"][0]["symbol"] == "BRC"

        assert len(data["top_losers"]) == 3
        assert data["top_losers"][0]["symbol"] == "EFT"

        assert data["highest_volume"]["symbol"] == "BTC"

class TestCsvReporter:
    def test_csv_reporter(self, sample_coins, tmp_path):
        file_path = tmp_path / "test_csv_report.csv"
        reporter = CsvReporter(filename=str(file_path))

        portfolio = CryptoPortfolio(sample_coins)
        reporter.report(portfolio, "TestCsvProvider", top_count=3)

        assert file_path.exists()

        content = file_path.read_text(encoding="utf-8")

        assert "TestCsvProvider" in content
        assert "BRC" in content
        assert "TMS" in content

class TestConsolReporter:
    def test_console_reporter(self, sample_coins):
        output = StringIO()
        fake_console = Console(file=output)

        reporter = ConsoleReporter()
        reporter.console = fake_console

        portfolio = CryptoPortfolio(sample_coins)
        reporter.report(portfolio, "TestConsoleProvider", top_count=3)

        result = output.getvalue()

        assert "TestConsoleProvider" in result
        assert "BRC" in result
        assert "TMS" in result



