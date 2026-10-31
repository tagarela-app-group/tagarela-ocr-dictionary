from unittest.mock import patch

from django.db.utils import OperationalError
from rest_framework.test import APISimpleTestCase


@patch("config.health.connections")
class HealthViewTests(APISimpleTestCase):
    def test_open_without_login(self, connections):
        response = self.client.get("/health", headers={"Authorization": "Bearer invalido"})

        self.assertEqual(response.status_code, 200)

    def test_database_up_returns_200(self, connections):
        response = self.client.get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok", "checks": {"database": True}})

    def test_database_down_returns_503(self, connections):
        connections["default"].ensure_connection.side_effect = OperationalError("down")

        response = self.client.get("/health")

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json(), {"status": "unhealthy", "checks": {"database": False}})
