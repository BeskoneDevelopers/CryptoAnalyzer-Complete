import csv
import json
from io import StringIO

import pytest
from rich.console import Console

from models import CryptoPortfolio
from reporters import get_reporter


def _section_rows(rows, start_index):
    section_rows = []

    for row in rows[start_index + 1:]:
        if not row:
            break
        section_rows.append(row)

    return section_rows


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
        gainers_rows = _section_rows(rows, gainers_header_index)

        losers_header_index = rows.index(
            header,
            gainers_header_index + 1,
        )
        losers_rows = _section_rows(rows, losers_header_index)

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



