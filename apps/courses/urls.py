from django.urls import path

from apps.courses.views import CourseActivateView, CourseListView

urlpatterns = [
    path("courses", CourseListView.as_view(), name="courses"),
    path(
        "courses/<uuid:course_id>/activate",
        CourseActivateView.as_view(),
        name="course_activate",
    ),
]
