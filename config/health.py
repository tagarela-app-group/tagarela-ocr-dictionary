from django.conf import settings
from django.db import connections
from django.db.utils import OperationalError
from redis import Redis
from redis.exceptions import RedisError
from rest_framework import status
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response


def _database_status() -> bool:
    try:
        connections["default"].ensure_connection()
    except OperationalError:
        return False

    return True


def _redis_status() -> bool:
    try:
        Redis.from_url(settings.REDIS_URL, socket_connect_timeout=1).ping()
    except RedisError:
        return False

    return True


@api_view(["GET"])
@authentication_classes([])
@permission_classes([AllowAny])
def health(request):
    checks = {
        "database": _database_status(),
        "redis": _redis_status(),
    }
    is_healthy = all(checks.values())
    response_status = status.HTTP_200_OK if is_healthy else status.HTTP_503_SERVICE_UNAVAILABLE

    return Response(
        {
            "status": "ok" if is_healthy else "unhealthy",
            "checks": checks,
        },
        status=response_status,
    )
