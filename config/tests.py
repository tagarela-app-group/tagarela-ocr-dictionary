from unittest.mock import patch

from django.db.utils import OperationalError
from django.test import override_settings
from redis.exceptions import RedisError
from rest_framework.test import APISimpleTestCase


@override_settings(REDIS_URL="redis://redis.test:6379/0")
@patch("config.health.Redis")
@patch("config.health.connections")
class HealthViewTests(APISimpleTestCase):
    def test_database_and_redis_up_returns_200(self, connections, redis):
        response = self.client.get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {"status": "ok", "checks": {"database": True, "redis": True}},
        )
        connections.__getitem__.assert_called_once_with("default")
        redis.from_url.assert_called_once_with(
            "redis://redis.test:6379/0", socket_connect_timeout=1
        )

    def test_database_down_returns_503(self, connections, redis):
        connections["default"].ensure_connection.side_effect = OperationalError("down")

        response = self.client.get("/health")

        self.assertEqual(response.status_code, 503)
        self.assertEqual(
            response.json(),
            {"status": "unhealthy", "checks": {"database": False, "redis": True}},
        )

    def test_redis_down_returns_503(self, connections, redis):
        redis.from_url.return_value.ping.side_effect = RedisError("down")

        response = self.client.get("/health")

        self.assertEqual(response.status_code, 503)
        self.assertEqual(
            response.json(),
            {"status": "unhealthy", "checks": {"database": True, "redis": False}},
        )
