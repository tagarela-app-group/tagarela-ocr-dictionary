from django.urls import path

from apps.vocabulary.views import (
    GroupDetailView,
    create_group,
    delete_terms,
    move_terms,
    restore_terms,
    vocabulary,
)

urlpatterns = [
    path("vocabulary", vocabulary, name="vocabulary"),
    path("groups", create_group, name="groups"),
    path("groups/<uuid:group_id>", GroupDetailView.as_view(), name="group"),
    path("terms/move", move_terms, name="terms_move"),
    path("terms/delete", delete_terms, name="terms_delete"),
    path("terms/restore", restore_terms, name="terms_restore"),
]
