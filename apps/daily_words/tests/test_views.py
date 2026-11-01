import json
from datetime import date, timedelta
from unittest.mock import patch

from rest_framework.test import APITestCase

from apps.captures.tests.helpers import make_user
from apps.courses.tests.helpers import make_course
from apps.daily_words.models import DailyWord
from apps.exercises.tests.helpers import StubProvider
from apps.language_analysis.providers.gemini import GeminiUnavailableError
from apps.vocabulary.models import Term
from apps.vocabulary.tests.helpers import make_term

HANGRY = {
    "source_word": "hangry",
    "phonetic": "/ˈhæŋ.ɡri/",
    "source_example": "Feed me, I'm getting hangry!",
    "target_meaning": "com fome e de mau humor",
}
TODAY = date(2026, 11, 1)


class DailyWordTests(APITestCase):
    def setUp(self):
        super().setUp()
        self.user = make_user()
        self.client.force_authenticate(self.user)
        self.course = make_course(self.user)
        self.provider = StubProvider(response=HANGRY)
        self.use(self.provider)
        self.at(TODAY)

    def use(self, provider: StubProvider) -> None:
        stub = patch("apps.daily_words.services.GeminiProvider", return_value=provider)
        stub.start()
        self.addCleanup(stub.stop)

    def at(self, day: date) -> None:
        stub = patch("apps.daily_words.services.timezone.localdate", return_value=day)
        stub.start()
        self.addCleanup(stub.stop)

    def get(self):
        return self.client.get("/api/v1/daily-word")

    def save(self):
        return self.client.post("/api/v1/daily-word/save")

    def learner(self, call: int = 0) -> dict[str, object]:
        return json.loads(self.provider.calls[call]["prompt"].split("\n", 1)[1])

    def test_generates_once_a_day_and_keeps_the_word(self):
        first = self.get()
        second = self.get()

        self.assertEqual(first.status_code, 200)
        self.assertEqual(first.json()["text"], "hangry")
        self.assertEqual(first.json()["kind"], "word")
        self.assertEqual(first.json()["term"], None)
        self.assertEqual(second.json(), first.json())
        self.assertEqual(len(self.provider.calls), 1)

    def test_expression_is_stored_as_expression(self):
        self.use(StubProvider(response={**HANGRY, "source_word": "on  the fence"}))

        body = self.get().json()

        self.assertEqual((body["text"], body["kind"]), ("on the fence", "expression"))

    def test_next_day_avoids_past_words_and_the_vocabulary(self):
        make_term(self.user, "awkward", course=self.course)
        self.get()
        self.at(TODAY + timedelta(days=1))

        self.get()

        self.assertEqual(len(self.provider.calls), 2)
        self.assertEqual(set(self.learner(1)["avoid"]), {"hangry", "awkward"})

    def test_uses_the_languages_of_the_active_course(self):
        make_course(self.user, learning="es", base="en", active=True)

        self.get()

        learner = self.learner()
        self.assertEqual((learner["source_language"], learner["target_language"]), ("es", "en"))

    def test_each_course_has_its_own_word(self):
        self.get()
        make_course(self.user, learning="es", base="pt", active=True)

        self.get()

        self.assertEqual(DailyWord.objects.count(), 2)

    def test_invalid_answer_from_the_ai_saves_nothing(self):
        self.use(StubProvider(response={**HANGRY, "target_meaning": ""}))

        self.assertEqual(self.get().status_code, 502)
        self.assertFalse(DailyWord.objects.exists())

    def test_ai_down_saves_nothing_and_tries_again_later(self):
        self.use(StubProvider(error=GeminiUnavailableError()))
        self.assertEqual(self.get().status_code, 503)
        self.assertFalse(DailyWord.objects.exists())

        self.use(StubProvider(response=HANGRY))
        self.assertEqual(self.get().status_code, 200)

    def test_without_course_there_is_no_word(self):
        self.client.force_authenticate(make_user("sem@example.com"))

        self.assertEqual(self.get().status_code, 404)

    def test_save_adds_to_the_vocabulary_and_is_idempotent(self):
        first = self.save()
        second = self.save()

        self.assertEqual(first.status_code, 201)
        self.assertEqual(first.json()["term"]["text"], "hangry")
        self.assertEqual(second.json()["term"]["id"], first.json()["term"]["id"])
        self.assertEqual(Term.objects.filter(course=self.course).count(), 1)

    def test_word_already_in_the_vocabulary_comes_with_the_term(self):
        term = make_term(self.user, "Hangry", course=self.course)

        self.assertEqual(self.get().json()["term"]["id"], str(term.id))

    def test_deleted_term_is_not_saved_until_saved_again(self):
        term = make_term(self.user, "hangry", course=self.course)
        term.deleted_at = term.created_at
        term.save(update_fields=["deleted_at"])

        self.assertEqual(self.get().json()["term"], None)
        self.assertEqual(self.save().json()["term"]["id"], str(term.id))
