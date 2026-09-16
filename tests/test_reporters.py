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

def make_report_data(sample_coins, provider):

    highest = max(
        sample_coins,
        key=lambda coin: coin.total_volume or 0,
    )

    return {
        "generated_at": "2026-07-15 11:30:00",
        "provider": provider,
        "total_coins": len(sample_coins),
        "total_market_cap": sum(
            coin.market_cap
            for coin in sample_coins
            if coin.market_cap is not None
        ),
        "top_gainers": [
            {
                "name": coin.name,
                "symbol": coin.symbol,
                "price": coin.current_price,
                "24h_change": coin.price_change_for_24h,
            }
            for coin in sorted(
                sample_coins,
                key=lambda coin: coin.price_change_for_24h or float("-inf"),
                reverse=True,
            )[:3]
        ],
        "top_losers": [
            {
                "name": coin.name,
                "symbol": coin.symbol,
                "price": coin.current_price,
                "24h_change": coin.price_change_for_24h,
            }
            for coin in sorted(
                sample_coins,
                key=lambda coin: coin.price_change_for_24h or float("inf"),
            )[:3]
        ],
        "all_coins": [
            {
                "name": coin.name,
                "symbol": coin.symbol,
                "price": coin.current_price,
                "volume_24h": coin.total_volume,
                "24h_change": coin.price_change_for_24h,
            }
            for coin in sample_coins
        ],
        "highest_volume": {
            "name": highest.name,
            "symbol": highest.symbol,
            "volume": highest.total_volume,
        }
    }


class TestJsonReporter:

    def test_json_reporter(self, sample_coins, tmp_path):
        filepath = tmp_path / "test_mega_report.json"
        reporter = get_reporter("json")
        reporter.filename = str(filepath)

        data = make_report_data(sample_coins, "TestJsonProvider")
        reporter.report(data)

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

        data = make_report_data(sample_coins, "TestCsvProvider")
        reporter.report(data)

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

        data = make_report_data(sample_coins, "TestConsoleProvider")
        reporter.report(data)

        result = output.getvalue()

        assert "TestConsoleProvider" in result
        assert "BRC" in result
        assert "TMS" in result



