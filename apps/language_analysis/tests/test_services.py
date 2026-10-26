from django.test import SimpleTestCase, override_settings

from apps.language_analysis.integrations.gemini_provider import GeminiInvalidResponseError
from apps.language_analysis.services import LinguisticAnalysisService
from apps.language_analysis.tests.helpers import VALID_ANALYSIS


class StubProvider:
    def __init__(self, response):
        self.response = response
        self.prompt = None

    def analyze(self, prompt):
        self.prompt = prompt
        return self.response


@override_settings(GEMINI_MODEL="gemini-3.5-flash-lite")
class LinguisticAnalysisServiceTests(SimpleTestCase):
    def analyze(self, data=None, response=None):
        provider = StubProvider(response or VALID_ANALYSIS)
        result = LinguisticAnalysisService(provider).analyze(
            {
                "text": "I run a small business.",
                "selected_term": "run",
                "source_language": "en",
                "target_language": "pt-BR",
                "level": "B1",
                **(data or {}),
            }
        )
        return result, provider

    def test_analyzes_a_contextualized_word(self):
        result, provider = self.analyze()

        self.assertEqual(result["analysis"], VALID_ANALYSIS)
        self.assertEqual(
            result["metadata"], {"model": "gemini-3.5-flash-lite", "prompt_version": "2.5"}
        )
        self.assertIn('"selected_term":"run"', provider.prompt)

    def test_analyzes_an_isolated_word_without_claiming_context(self):
        result, provider = self.analyze(
            data={"text": "run", "selected_term": None, "source_language": "auto", "level": None}
        )

        self.assertEqual(result["input"]["text"], "run")
        self.assertIn('"source_language":"auto"', provider.prompt)

    def test_passes_an_idiomatic_expression_as_untrusted_input(self):
        _, provider = self.analyze(
            data={
                "text": "She told a joke to break the ice.",
                "selected_term": "break the ice",
            }
        )

        self.assertIn('"selected_term":"break the ice"', provider.prompt)
        self.assertIn("untrusted", provider.prompt)

    def test_rejects_an_invalid_provider_response(self):
        invalid = {**VALID_ANALYSIS, "focus": "", "unexpected": "value"}

        with self.assertRaises(GeminiInvalidResponseError):
            self.analyze(response=invalid)

    def test_rejects_a_response_without_the_card_fields(self):
        for field, value in (
            ("formality", "casual"),
            ("contexts", None),
            ("source_contexts", None),
            ("source_formality_note", ""),
            ("phonetic", ""),
            ("literal", ""),
            ("dialogue", [{"speaker": "C", "text": "Hi.", "translation": "Oi."}]),
        ):
            with self.subTest(field=field), self.assertRaises(GeminiInvalidResponseError):
                self.analyze(response={**VALID_ANALYSIS, field: value})
