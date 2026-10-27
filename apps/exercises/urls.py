from django.urls import path

from apps.exercises.views import term_exercises

urlpatterns = [
    path("terms/<uuid:term_id>/exercises/<str:kind>", term_exercises, name="term_exercises"),
]
