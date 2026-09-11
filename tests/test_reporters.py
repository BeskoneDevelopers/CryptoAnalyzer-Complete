from models import CryptoPortfolio

from reporters import JsonReporter, CsvReporter, ConsoleReporter, get_reporter

import json
import pytest
import csv

from io import StringIO
from rich.console import Console


class TestReporter:
    def test_get_reporter_unknown_format(self):
        with pytest.raises(ValueError):
            get_reporter("unknown")


class TestJsonReporter:

    def test_json_reporter(self, sample_coins, tmp_path):
        filepath = tmp_path / "test_mega_report.json"
        reporter = get_reporter("json")
        reporter.filename = str(filepath)

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
        assert data["top_losers"][0]["symbol"] == "TMS"

        assert data["highest_volume"]["symbol"] == "BTC"

class TestCsvReporter:
    def test_csv_reporter(self, sample_coins, tmp_path):
        file_path = tmp_path / "test_csv_report.csv"
        reporter = get_reporter("csv")
        reporter.filename = str(file_path)

        portfolio = CryptoPortfolio(sample_coins)
        reporter.report(portfolio, "TestCsvProvider", top_count=3)

        assert file_path.exists()

        content = file_path.read_text(encoding="utf-8")
        rows = list(csv.reader(content.splitlines()))

        assert rows[2] == ["Provider: TestCsvProvider"]

        header = ["Name", "Symbol", "Price", "24h Change"]

        gainers_header_index = rows.index(header)
        gainers_rows = []

        for row in rows[gainers_header_index + 1:]:
            if not row:
                break
            gainers_rows.append(row)

        losers_header_index = rows.index(
            header,
            gainers_header_index + 1,
        )
        losers_rows = []

        for row in rows[losers_header_index + 1:]:
            if not row:
                break
            losers_rows.append(row)

        gainers_symbols = [row[1] for row in gainers_rows]
        losers_symbols = [row[1] for row in losers_rows]

        assert "BRC" in gainers_symbols
        assert "TMS" in losers_symbols

class TestConsolReporter:
    def test_console_reporter(self, sample_coins):
        output = StringIO()
        fake_console = Console(file=output)

        reporter = get_reporter("console")
        reporter.console = fake_console

        portfolio = CryptoPortfolio(sample_coins)
        reporter.report(portfolio, "TestConsoleProvider", top_count=3)

        result = output.getvalue()

        assert "TestConsoleProvider" in result
        assert "BRC" in result
        assert "TMS" in result



