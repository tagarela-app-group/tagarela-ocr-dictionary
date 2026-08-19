from django.urls import path

from apps.ocr.views import analyze_image

urlpatterns = [
    path("analyze", analyze_image, name="analyze_image"),
]
