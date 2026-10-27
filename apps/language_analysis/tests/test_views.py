from unittest.mock import patch

from rest_framework.test import APITestCase

from apps.captures.tests.helpers import make_user
from apps.language_analysis.tests.helpers import VALID_ANALYSIS

URL = "/api/v1/language-analysis/analyze"


class LanguageAnalysisViewTests(APITestCase):
    def setUp(self):
        self.user = make_user()
        self.client.force_authenticate(self.user)

    def payload(self, **overrides):
        return {
            "text": "I run a small business.",
            "selected_term": "run",
            "source_language": "en",
            "target_language": "pt-BR",
            "level": "B1",
            **overrides,
        }

    @patch("apps.language_analysis.views.LinguisticAnalysisService")
    def test_returns_an_analysis(self, service_class):
        service_class.return_value.analyze.return_value = {
            "input": self.payload(),
            "analysis": VALID_ANALYSIS,
            "metadata": {"model": "gemini-3.5-flash-lite", "prompt_version": "2.6"},
        }

        response = self.client.post(URL, self.payload(), format="json")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["analysis"], VALID_ANALYSIS)
        service_class.return_value.analyze.assert_called_once_with(self.payload())

    def test_requires_login(self):
        self.client.force_authenticate(None)

        self.assertEqual(self.client.post(URL, self.payload(), format="json").status_code, 401)

    @patch("apps.language_analysis.views.LinguisticAnalysisService")
    def test_defaults_languages_and_level(self, service_class):
        service_class.return_value.analyze.return_value = {
            "input": {
                "text": "run",
                "selected_term": None,
                "source_language": "auto",
                "target_language": "pt-BR",
                "level": None,
            },
            "analysis": VALID_ANALYSIS,
            "metadata": {"model": "gemini-3.5-flash-lite", "prompt_version": "2.6"},
        }
        response = self.client.post(URL, {"text": "run"}, format="json")

        self.assertEqual(response.status_code, 200)
        service_class.return_value.analyze.assert_called_once_with(
            {
                "text": "run",
                "source_language": "auto",
                "target_language": "pt-BR",
                "level": None,
            }
        )

    def test_rejects_empty_or_too_long_text(self):
        for text in ("   ", "x" * 3001):
            with self.subTest(text_length=len(text)):
                response = self.client.post(URL, self.payload(text=text), format="json")

                self.assertEqual(response.status_code, 400)
                self.assertIn("text", response.json())

    def test_rejects_invalid_languages_and_level(self):
        for field, value in (
            ("source_language", "english"),
            ("target_language", "auto"),
            ("level", "Z9"),
        ):
            with self.subTest(field=field):
                response = self.client.post(URL, self.payload(**{field: value}), format="json")

                self.assertEqual(response.status_code, 400)
                self.assertIn(field, response.json())

    def test_rejects_unknown_fields(self):
        response = self.client.post(URL, self.payload(unexpected=True), format="json")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["unexpected"], ["Unknown field."])
