from unittest.mock import patch

import pytest
from django.test import TestCase

from analyzer.models import Coin, CoinPrice, Snapshot
from analyzer.tasks import fetch_snapshot_task


@pytest.mark.integration
class SnapshotTaskTest(TestCase):
    @patch("analyzer.tasks._fetch_data")
    def test_fetch_snapshot_task(self, mock_fetch):
        mock_fetch.return_value = [
            {
                "name": "Bitcoin",
                "symbol": "btc",
                "current_price": 100,
                "total_volume": 1000,
                "price_change_percentage_24h": 1,
            }
        ]

        result = fetch_snapshot_task.run(provider="test", limit=1)

        self.assertEqual(result["total_coins"], 1)

        self.assertEqual(Snapshot.objects.count(), 1)

        self.assertEqual(Coin.objects.count(), 1)

        self.assertEqual(CoinPrice.objects.count(), 1)
