from django.urls import path

from apps.reviews.views import record_attempt, review_session

urlpatterns = [
    path("reviews", review_session, name="reviews"),
    path("reviews/attempts", record_attempt, name="review_attempts"),
]
