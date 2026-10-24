from django.urls import path

from apps.captures.views import (
    CaptureConfirmView,
    CaptureDetailView,
    CaptureListView,
)

urlpatterns = [
    path("captures", CaptureListView.as_view(), name="captures"),
    path("captures/<uuid:capture_id>", CaptureDetailView.as_view(), name="capture"),
    path(
        "captures/<uuid:capture_id>/confirm",
        CaptureConfirmView.as_view(),
        name="capture_confirm",
    ),
]
