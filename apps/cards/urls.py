from django.urls import path

from apps.cards.views import TermDetailView

urlpatterns = [
    path("terms/<uuid:term_id>", TermDetailView.as_view(), name="term"),
]
