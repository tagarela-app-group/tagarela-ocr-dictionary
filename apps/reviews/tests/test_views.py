import uuid

from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APITestCase

from apps.captures.tests.helpers import make_user
from apps.courses.models import Course
from apps.courses.tests.helpers import make_course
from apps.exercises.models import Exercise
from apps.reviews.models import ReviewAttempt
from apps.reviews.policy import MASTERED_LEVEL
from apps.vocabulary.tests.helpers import api_datetime, make_term


def make_exercise(term, variant: int = 0) -> Exercise:
    return Exercise.objects.create(
        term=term,
        kind=Exercise.Kind.LISTEN_WRITE,
        variant=variant,
        payload={"sentence": term.text},
        prompt_version="1.0",
        model="m",
    )


class ReviewSessionTests(APITestCase):
    def setUp(self):
        super().setUp()
        self.user = make_user()
        self.client.force_authenticate(self.user)
        self.course = make_course(self.user)

    def session(self, query: str = "?kinds=listen_write"):
        response = self.client.get(f"/api/v1/reviews{query}")
        self.assertEqual(response.status_code, 200)
        return response.json()

    def test_lists_every_term_not_yet_mastered(self):
        fence = make_term(self.user, "on the fence", course=self.course, level=2)
        awkward = make_term(self.user, "awkward", course=self.course)
        make_term(self.user, "sleep on it", course=self.course, level=MASTERED_LEVEL)
        gone = make_term(self.user, "gone", course=self.course)
        gone.deleted_at = timezone.now()
        gone.save(update_fields=["deleted_at"])
        make_term(self.user, "en las nubes", course=make_course(self.user, "es", "pt"))

        session = self.session()

        self.assertEqual(session["due"], 2)
        self.assertCountEqual(
            session["rounds"],
            [
                {
                    "term": {
                        "id": str(term.id),
                        "text": term.text,
                        "translation": "",
                        "kind": term.kind,
                        "level": term.level,
                        "created_at": api_datetime(term.created_at),
                    },
                    "kind": "listen_write",
                }
                for term in (fence, awkward)
            ],
        )

    @override_settings(REVIEW_SESSION_SIZE=2)
    def test_session_takes_the_least_reviewed_terms_first(self):
        for text, level in (("a lot", 3), ("bite", 0), ("cheer up", 4), ("dull", 1)):
            make_term(self.user, text, course=self.course, level=level)

        session = self.session()

        self.assertEqual(session["due"], 4)
        self.assertCountEqual([r["term"]["text"] for r in session["rounds"]], ["bite", "dull"])

    def test_without_course_is_empty_and_creates_nothing(self):
        self.client.force_authenticate(make_user("bia@example.com"))

        self.assertEqual(self.session(), {"due": 0, "rounds": []})
        self.assertFalse(Course.objects.filter(user__email="bia@example.com").exists())

    def test_without_known_kinds_there_are_no_rounds(self):
        make_term(self.user, "awkward", course=self.course)

        session = self.session("?kinds=crossword")

        self.assertEqual(session, {"due": 1, "rounds": []})

    def test_without_kinds_every_known_kind_is_allowed(self):
        make_term(self.user, "awkward", course=self.course)

        session = self.session("")

        self.assertEqual(session["rounds"][0]["kind"], "listen_write")


class ReviewAttemptTests(APITestCase):
    def setUp(self):
        super().setUp()
        self.user = make_user()
        self.client.force_authenticate(self.user)
        self.term = make_term(self.user, "on the fence", level=1)
        self.exercise = make_exercise(self.term)

    def attempt(self, **fields):
        data = {
            "term": str(self.term.id),
            "kind": "listen_write",
            "exercise": str(self.exercise.id),
            "outcome": "first",
            **fields,
        }
        return self.client.post("/api/v1/reviews/attempts", data, format="json")

    def test_a_review_moves_the_term_one_level_up(self):
        response = self.attempt(outcome="hint")

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["term"]["level"], 2)
        self.term.refresh_from_db()
        self.assertEqual(self.term.level, 2)
        attempt = ReviewAttempt.objects.get()
        self.assertEqual(
            (attempt.exercise, attempt.outcome, attempt.level), (self.exercise, "hint", 2)
        )
        self.exercise.refresh_from_db()
        self.assertEqual(self.exercise.served_count, 1)

    def test_same_attempt_again_does_not_move_the_level_twice(self):
        attempt_id = str(uuid.uuid4())

        first = self.attempt(id=attempt_id)
        again = self.attempt(id=attempt_id)

        self.assertEqual(first.status_code, 201)
        self.assertEqual(again.status_code, 201)
        self.assertEqual(again.json()["term"]["level"], 2)
        self.assertEqual(ReviewAttempt.objects.count(), 1)
        self.exercise.refresh_from_db()
        self.assertEqual(self.exercise.served_count, 1)

    def test_id_used_on_another_term_returns_409(self):
        attempt_id = str(uuid.uuid4())
        other = make_term(self.user, "awkward", course=self.term.course)
        self.attempt(id=attempt_id)

        response = self.attempt(id=attempt_id, term=str(other.id), exercise=None)

        self.assertEqual(response.status_code, 409)
        other.refresh_from_db()
        self.assertEqual(other.level, 0)

    def test_seeing_the_answer_keeps_the_level(self):
        response = self.attempt(outcome="missed")

        self.assertEqual(response.json()["term"]["level"], 1)
        self.assertEqual(ReviewAttempt.objects.get().outcome, "missed")

    def test_level_stops_at_mastered(self):
        self.term.level = MASTERED_LEVEL
        self.term.save(update_fields=["level"])

        response = self.attempt()

        self.assertEqual(response.json()["term"]["level"], MASTERED_LEVEL)

    def test_attempt_without_exercise_is_recorded(self):
        response = self.attempt(exercise=None, outcome="retry")

        self.assertEqual(response.status_code, 201)
        self.assertIsNone(ReviewAttempt.objects.get().exercise)

    def test_exercise_of_another_term_is_rejected(self):
        other = make_exercise(make_term(self.user, "awkward", course=self.term.course))

        response = self.attempt(exercise=str(other.id))

        self.assertEqual(response.status_code, 400)
        self.assertIn("exercise", response.json())
        self.term.refresh_from_db()
        self.assertEqual(self.term.level, 1)

    def test_term_of_someone_else_is_not_found(self):
        other = make_term(make_user("bia@example.com"), "on the fence")

        response = self.attempt(term=str(other.id), exercise=None)

        self.assertEqual(response.status_code, 404)

    def test_unknown_fields_and_outcomes_are_rejected(self):
        response = self.attempt(outcome="perfect", score=10)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(set(response.json()), {"outcome", "score"})
