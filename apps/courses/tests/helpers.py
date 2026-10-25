from apps.courses.models import Course
from apps.courses.services import CourseService


def make_course(user, learning: str = "en", base: str = "pt", active: bool = False) -> Course:
    course, _ = Course.objects.get_or_create(user=user, learning=learning, base=base)
    if active or not Course.objects.filter(user=user, active=True).exists():
        CourseService().activate(course)

    return course
