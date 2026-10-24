from django.urls import path

from apps.vocabulary.views import create_group, move_terms, vocabulary

urlpatterns = [
    path("vocabulary", vocabulary, name="vocabulary"),
    path("groups", create_group, name="groups"),
    path("terms/move", move_terms, name="terms_move"),
]
