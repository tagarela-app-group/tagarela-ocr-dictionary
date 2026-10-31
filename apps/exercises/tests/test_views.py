import json
from unittest.mock import patch

from django.test import override_settings
from rest_framework.test import APITestCase

from apps.captures.tests.helpers import make_user
from apps.cards.models import TermCard
from apps.courses.tests.helpers import make_course
from apps.exercises.kinds.listen_write import PROMPT_VERSION
from apps.exercises.models import Exercise
from apps.exercises.tests.helpers import FENCE_ITEMS, StubProvider
from apps.language_analysis.providers.gemini import GeminiUnavailableError
from apps.vocabulary.tests.helpers import make_term


class TermExercisesTests(APITestCase):
    def setUp(self):
        super().setUp()
        self.user = make_user()
        self.client.force_authenticate(self.user)
        self.term = make_term(self.user, "on the fence")
        self.provider = StubProvider()
        self.use(self.provider)

    def use(self, provider: StubProvider) -> None:
        stub = patch("apps.exercises.services.GeminiProvider", return_value=provider)
        stub.start()
        self.addCleanup(stub.stop)

    def get(self, term=None, kind="listen_write"):
        return self.client.get(f"/api/v1/terms/{(term or self.term).id}/exercises/{kind}")

    def brief(self) -> dict[str, object]:
        prompt = self.provider.calls[0]["prompt"]
        return json.loads(prompt.split("\n", 1)[1])

    @override_settings(GEMINI_MODEL="configured-model")
    def test_first_request_generates_and_stores_the_variations(self):
        response = self.get()

        self.assertEqual(response.status_code, 200)
        exercises = response.json()["exercises"]
        self.assertEqual([e["variant"] for e in exercises], [0, 1, 2])
        self.assertEqual({e["kind"] for e in exercises}, {"listen_write"})
        self.assertEqual(exercises[0]["payload"]["sentence"], FENCE_ITEMS[0]["source_sentence"])
        self.assertEqual(exercises[0]["payload"]["start"], 10)
        stored = Exercise.objects.get(pk=exercises[0]["id"])
        self.assertEqual(
            (stored.prompt_version, stored.model), (PROMPT_VERSION, "configured-model")
        )
        call = self.provider.calls[0]
        self.assertEqual(call["schema"]["properties"]["items"]["maxItems"], 3)
        self.assertEqual(
            self.brief(),
            {
                "focus": "on the fence",
                "focus_kind": "expression",
                "source_language": "en",
                "target_language": "pt-BR",
                "meaning": None,
                "count": 3,
            },
        )

    def test_next_requests_reuse_the_stored_variations(self):
        first = self.get().json()

        second = self.get()

        self.assertEqual(second.json(), first)
        self.assertEqual(len(self.provider.calls), 1)

    def test_least_served_variation_comes_first(self):
        self.get()
        Exercise.objects.filter(variant=0).update(served_count=2)
        Exercise.objects.filter(variant=1).update(served_count=1)

        exercises = self.get().json()["exercises"]

        self.assertEqual([e["variant"] for e in exercises], [2, 1, 0])

    def test_uses_the_meaning_and_languages_of_the_card(self):
        user = make_user("carla@example.com")
        self.client.force_authenticate(user)
        term = make_term(user, "estar en las nubes", course=make_course(user, "es", "en"))
        TermCard.objects.create(
            term=term,
            analysis={"source_meaning_in_context": "estar distraído"},
            prompt_version="2.6",
            model="m",
        )

        self.get(term)

        brief = self.brief()
        self.assertEqual(brief["meaning"], "estar distraído")
        self.assertEqual((brief["source_language"], brief["target_language"]), ("es", "en"))

    @override_settings(EXERCISE_VARIATIONS=2)
    def test_keeps_at_most_the_configured_variations(self):
        exercises = self.get().json()["exercises"]

        self.assertEqual(len(exercises), 2)
        self.assertEqual(self.brief()["count"], 2)

    def test_invalid_response_stores_nothing(self):
        self.use(StubProvider({"items": [{"source_sentence": "x"}]}))

        response = self.get()

        self.assertEqual(response.status_code, 502)
        self.assertFalse(Exercise.objects.exists())

    def test_provider_failure_is_reported(self):
        self.use(StubProvider(error=GeminiUnavailableError()))

        self.assertEqual(self.get().status_code, 503)

    def test_unknown_kind_is_not_found(self):
        response = self.get(kind="crossword")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(self.provider.calls, [])

    def test_term_of_someone_else_is_not_found(self):
        other = make_term(make_user("bia@example.com"), "on the fence")

        self.assertEqual(self.get(other).status_code, 404)

    def test_deleted_term_is_not_found(self):
        self.term.deleted_at = self.term.created_at
        self.term.save(update_fields=["deleted_at"])

        self.assertEqual(self.get().status_code, 404)
