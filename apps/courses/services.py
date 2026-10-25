from django.db import transaction
from django.db.models import Count, Q
from django.http import Http404

from apps.courses.models import Course


class CourseService:
    def courses(self, user):
        return Course.objects.filter(user=user).annotate(
            term_count=Count("terms", filter=Q(terms__deleted_at__isnull=True))
        )

    def course(self, user, course_id) -> Course:
        course = self.courses(user).filter(pk=course_id).first()
        if course is None:
            raise Http404

        return course

    def active(self, user) -> Course:
        course = Course.objects.filter(user=user, active=True).first()
        if course is not None:
            return course

        course, _ = self.start(user, Course.Language.EN, Course.Language.PT)
        return course

    @transaction.atomic
    def start(self, user, learning: str, base: str) -> tuple[Course, bool]:
        course, created = Course.objects.get_or_create(user=user, learning=learning, base=base)
        self.activate(course)

        return course, created

    @transaction.atomic
    def activate(self, course: Course) -> Course:
        list(Course.objects.select_for_update().filter(user_id=course.user_id))
        Course.objects.filter(user_id=course.user_id, active=True).exclude(pk=course.pk).update(
            active=False
        )
        if not course.active:
            course.active = True
            course.save(update_fields=["active"])

        return course
