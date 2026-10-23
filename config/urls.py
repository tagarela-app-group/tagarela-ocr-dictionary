from django.contrib import admin
from django.urls import include, path

from config.health import health

urlpatterns = [
    path("admin/", admin.site.urls),
    path("health", health, name="health"),
    path("api/v1/images/", include("apps.ocr.urls")),
    path("api/auth/", include("allauth.headless.urls")),
]
