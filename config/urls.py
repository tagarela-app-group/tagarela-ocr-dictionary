from django.contrib import admin
from django.urls import include, path

from config.health import health

urlpatterns = [
    path("admin/", admin.site.urls),
    path("health", health, name="health"),
    path("api/v1/", include("apps.courses.urls")),
    path("api/v1/", include("apps.captures.urls")),
    path("api/v1/", include("apps.vocabulary.urls")),
    path("api/v1/", include("apps.cards.urls")),
    path("api/v1/", include("apps.exercises.urls")),
    path("api/v1/", include("apps.reviews.urls")),
    path("api/v1/", include("apps.accounts.urls")),
    path("api/auth/", include("allauth.headless.urls")),
]
