from unittest.mock import patch

from django.test import SimpleTestCase


class HealthCheckTests(SimpleTestCase):
    @patch("analyzer.health._check_database")
    @patch("analyzer.health._check_cache")
    @patch("analyzer.health._check_celery_broker")
    def test_health_returns_200_when_all_services_are_available(
        self,
        mock_celery_broker,
        mock_cache,
        mock_database,
    ):
        mock_database.return_value = True
        mock_cache.return_value = True
        mock_celery_broker.return_value = True

        response = self.client.get("/health/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")

    @patch("analyzer.health._check_database")
    @patch("analyzer.health._check_cache")
    @patch("analyzer.health._check_celery_broker")
    def test_health_returns_503_when_service_is_unavailable(
        self,
        mock_celery_broker,
        mock_cache,
        mock_database,
    ):
        mock_database.return_value = True
        mock_cache.return_value = False
        mock_celery_broker.return_value = True

        response = self.client.get("/health/")

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["status"], "degraded")
        self.assertEqual(response.json()["database"], "ok")
        self.assertEqual(response.json()["redis"], "error")
        self.assertEqual(response.json()["celery_broker"], "ok")
