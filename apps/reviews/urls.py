from django.urls import path

from apps.reviews.views import ask_for_more, record_attempt, review_session, study_term

urlpatterns = [
    path("reviews", review_session, name="reviews"),
    path("reviews/attempts", record_attempt, name="review_attempts"),
    path("reviews/more", ask_for_more, name="reviews_more"),
    path("terms/<uuid:term_id>/study", study_term, name="term_study"),
]
