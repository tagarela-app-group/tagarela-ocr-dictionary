from django.urls import path

from apps.language_analysis.views import LanguageAnalysisView

urlpatterns = [
    path("language-analysis/analyze", LanguageAnalysisView.as_view(), name="language_analysis"),
]
