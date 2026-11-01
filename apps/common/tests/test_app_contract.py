import json
import os
from pathlib import Path
from unittest import skipUnless
from unittest.mock import patch

from django.test import SimpleTestCase
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.test import APITestCase

from apps.captures.models import Capture, CaptureTerm
from apps.captures.tests.helpers import make_capture, make_user
from apps.cards.models import TermCard
from apps.courses.models import Course
from apps.courses.tests.helpers import make_course
from apps.exercises.tests.helpers import StubProvider
from apps.language_analysis.tests.helpers import VALID_ANALYSIS
from apps.vocabulary.models import Term
from apps.vocabulary.tests.helpers import make_group, make_term

CONTRACT_DIR = os.environ.get("APP_CONTRACT_DIR", "")

FULL_ANALYSIS = {
    **VALID_ANALYSIS,
    "literal": "repare no vão",
    "source_pitfall_wrong": "mind the hole",
    "source_pitfall_right": "mind the gap",
}


def shape_errors(example: object, real: object, path: str = "$") -> list[str]:
    if example is None:
        return []
    if isinstance(example, dict):
        if not isinstance(real, dict):
            return [f"{path}: expected object"]
        errors: list[str] = []
        for key, value in example.items():
            if key in real:
                errors += shape_errors(value, real[key], f"{path}.{key}")
            else:
                errors.append(f"{path}.{key}: missing")
        return errors
    if isinstance(example, list):
        if not isinstance(real, list):
            return [f"{path}: expected list"]
        if not example:
            return []
        if not real:
            return [f"{path}: empty list"]
        return [error for item in real for error in shape_errors(example[0], item, f"{path}[]")]
    if type(example) is not type(real):
        return [f"{path}: expected {type(example).__name__}, got {type(real).__name__}"]
    return []


class ShapeErrorsTests(SimpleTestCase):
    def test_accepts_a_field_the_app_does_not_read(self) -> None:
        self.assertEqual(shape_errors({"a": 1}, {"a": 2, "b": 3}), [])

    def test_reports_a_missing_field(self) -> None:
        self.assertEqual(shape_errors({"a": {"b": 1}}, {"a": {}}), ["$.a.b: missing"])

    def test_reports_a_changed_type_in_every_list_item(self) -> None:
        self.assertEqual(
            shape_errors({"a": [1]}, {"a": [2, "x"]}), ["$.a[]: expected int, got str"]
        )

    def test_bool_is_not_an_int(self) -> None:
        self.assertEqual(shape_errors(1, True), ["$: expected int, got bool"])

    def test_null_in_the_example_only_requires_the_field(self) -> None:
        self.assertEqual(shape_errors({"a": None}, {"a": "x"}), [])
        self.assertEqual(shape_errors({"a": None}, {}), ["$.a: missing"])

    def test_filled_list_in_the_example_rejects_an_empty_one(self) -> None:
        self.assertEqual(shape_errors([1], []), ["$: empty list"])


@skipUnless(CONTRACT_DIR, "APP_CONTRACT_DIR is only set in CI")
class AppContractTests(APITestCase):
    def setUp(self) -> None:
        super().setUp()
        self.user = make_user()
        self.client.force_authenticate(self.user)
        self.course = make_course(self.user)
        self.group = make_group(self.user, course=self.course)
        self.term = make_term(self.user, "mind the gap", self.group)
        make_term(self.user, "awkward", course=self.course)
        capture = make_capture(
            self.user,
            course=self.course,
            status=Capture.Status.ANALYZED,
            analyzed_at=timezone.now(),
        )
        start = capture.text.index(self.term.text)
        CaptureTerm.objects.create(
            capture=capture, text=self.term.text, start=start, end=start + len(self.term.text)
        )

    def example(self, name: str) -> dict:
        return json.loads((Path(CONTRACT_DIR) / f"{name}.json").read_text(encoding="utf-8"))

    def assert_matches(self, example: object, response: Response) -> None:
        self.assertLess(response.status_code, 300, response.content)
        self.assertEqual(shape_errors(example, response.json()), [])

    def test_capture_page(self) -> None:
        self.assert_matches(
            {"results": [self.example("capture")], "next": None},
            self.client.get("/api/v1/captures"),
        )

    def test_courses(self) -> None:
        self.assert_matches([self.example("course")], self.client.get("/api/v1/courses"))

    def test_vocabulary(self) -> None:
        self.assert_matches(self.example("vocabulary"), self.client.get("/api/v1/vocabulary"))

    def test_term_detail(self) -> None:
        TermCard.objects.create(
            term=self.term, analysis=FULL_ANALYSIS, prompt_version="contract", model="m"
        )

        with patch("apps.cards.services.LinguisticAnalysisService"):
            response = self.client.get(f"/api/v1/terms/{self.term.id}")

        self.assert_matches(self.example("term_detail"), response)

    def test_exercises(self) -> None:
        term = make_term(self.user, "on the fence", course=self.course)

        with patch("apps.exercises.services.GeminiProvider", return_value=StubProvider()):
            response = self.client.get(f"/api/v1/terms/{term.id}/exercises/listen_write")

        self.assert_matches(self.example("exercises"), response)

    def test_review_session(self) -> None:
        self.assert_matches(
            self.example("review_session"), self.client.get("/api/v1/reviews?kinds=listen_write")
        )

    def test_review_attempt(self) -> None:
        response = self.client.post(
            "/api/v1/reviews/attempts",
            {
                "term": str(self.term.id),
                "kind": "listen_write",
                "exercise": None,
                "outcome": "first",
            },
            format="json",
        )

        self.assert_matches(self.example("review_attempt"), response)

    def test_daily_word(self) -> None:
        provider = StubProvider(
            response={
                "source_word": "hangry",
                "phonetic": "/ˈhæŋ.ɡri/",
                "source_example": "Feed me, I'm getting hangry!",
                "target_meaning": "com fome e de mau humor",
            }
        )

        with patch("apps.daily_words.services.GeminiProvider", return_value=provider):
            response = self.client.post("/api/v1/daily-word/save")

        self.assert_matches(self.example("daily_word"), response)

    def test_account(self) -> None:
        response = self.client.patch("/api/v1/account", {"country": "BR"}, format="json")

        self.assert_matches(self.example("account"), response)

    def test_every_enum_value_is_accepted_by_the_app(self) -> None:
        enums = self.example("enums")

        for key, values in {
            "capture_source": Capture.Source.values,
            "capture_status": Capture.Status.values,
            "course_language": Course.Language.values,
            "term_kind": Term.Kind.values,
        }.items():
            self.assertLessEqual(set(values), set(enums[key]), key)
