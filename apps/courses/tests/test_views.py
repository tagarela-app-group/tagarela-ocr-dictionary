from django.utils import timezone
from rest_framework.test import APITestCase

from apps.captures.tests.helpers import make_user
from apps.courses.models import Course
from apps.courses.tests.helpers import make_course
from apps.vocabulary.tests.helpers import make_term

COURSES = "/api/v1/courses"


def activate_url(course) -> str:
    return f"{COURSES}/{course.id}/activate"


class CourseApiTestCase(APITestCase):
    def setUp(self):
        super().setUp()
        self.user = make_user()
        self.client.force_authenticate(self.user)

    def start(self, **data):
        return self.client.post(COURSES, {"learning": "es", "base": "en", **data}, format="json")

    def active(self):
        return Course.objects.get(user=self.user, active=True)


class ListCoursesTests(CourseApiTestCase):
    def test_new_account_has_no_course(self):
        response = self.client.get(COURSES)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])

    def test_lists_own_courses_oldest_first_with_their_terms(self):
        english = make_course(self.user)
        spanish = make_course(self.user, "es", "en")
        make_term(self.user, "layover")
        make_term(self.user, "gap", deleted_at=timezone.now())
        make_term(self.user, "hola", course=spanish)
        make_course(make_user("bia@example.com"), "pt", "es")

        response = self.client.get(COURSES)

        self.assertEqual(
            response.json(),
            [
                {
                    "id": str(english.id),
                    "learning": "en",
                    "base": "pt",
                    "active": True,
                    "terms": 1,
                },
                {
                    "id": str(spanish.id),
                    "learning": "es",
                    "base": "en",
                    "active": False,
                    "terms": 1,
                },
            ],
        )


class StartCourseTests(CourseApiTestCase):
    def test_creates_the_course_and_makes_it_active(self):
        english = make_course(self.user)

        response = self.start()

        self.assertEqual(response.status_code, 201)
        course = self.active()
        self.assertEqual((course.learning, course.base), ("es", "en"))
        self.assertEqual(
            response.json(),
            {"id": str(course.id), "learning": "es", "base": "en", "active": True, "terms": 0},
        )
        english.refresh_from_db()
        self.assertFalse(english.active)

    def test_same_pair_again_returns_it_active(self):
        spanish = make_course(self.user, "es", "en")
        make_course(self.user, active=True)

        response = self.start()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["id"], str(spanish.id))
        self.assertEqual(self.active(), spanish)
        self.assertEqual(Course.objects.filter(user=self.user).count(), 2)

    def test_same_target_through_another_language_is_another_course(self):
        make_course(self.user, "en", "pt")

        response = self.start(learning="en", base="es")

        self.assertEqual(response.status_code, 201)
        self.assertEqual(Course.objects.filter(user=self.user, learning="en").count(), 2)

    def test_learning_the_language_you_use_returns_400(self):
        response = self.start(learning="pt", base="pt")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json(),
            {"base": ["Escolha um idioma diferente do que você quer aprender."]},
        )
        self.assertFalse(Course.objects.exists())

    def test_invalid_body_returns_400(self):
        response = self.client.post(COURSES, {"learning": "fr", "active": True}, format="json")

        self.assertEqual(
            response.json(),
            {
                "learning": ["Escolha um idioma da lista."],
                "base": ["Escolha um idioma."],
                "active": ["Campo não permitido."],
            },
        )


class ActivateCourseTests(CourseApiTestCase):
    def test_switches_the_active_course(self):
        english = make_course(self.user)
        spanish = make_course(self.user, "es", "en")

        response = self.client.post(activate_url(spanish))

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["active"])
        self.assertEqual(self.active(), spanish)
        english.refresh_from_db()
        self.assertFalse(english.active)

    def test_active_course_again_is_fine(self):
        english = make_course(self.user)

        response = self.client.post(activate_url(english))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.active(), english)

    def test_course_of_another_user_returns_404(self):
        mine = make_course(self.user)
        other = make_course(make_user("bia@example.com"), "es", "en")

        response = self.client.post(activate_url(other))

        self.assertEqual(response.status_code, 404)
        self.assertEqual(self.active(), mine)
        other.refresh_from_db()
        self.assertTrue(other.active)
