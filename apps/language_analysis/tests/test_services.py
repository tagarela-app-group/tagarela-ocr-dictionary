from django.test import SimpleTestCase, override_settings

from apps.exercises.tests.helpers import StubProvider
from apps.language_analysis.prompts import PROMPT_VERSION
from apps.language_analysis.providers.gemini import GeminiInvalidResponseError
from apps.language_analysis.services import AnalysisResult, LinguisticAnalysisService
from apps.language_analysis.tests.helpers import VALID_ANALYSIS


@override_settings(GEMINI_MODEL="gemini-3.5-flash-lite")
class LinguisticAnalysisServiceTests(SimpleTestCase):
    def analyze(
        self, response: dict[str, object] | None = None
    ) -> tuple[AnalysisResult, StubProvider]:
        provider = StubProvider(response or VALID_ANALYSIS)
        result = LinguisticAnalysisService(provider).analyze(
            {
                "text": "I run a small business.",
                "selected_term": "run",
                "source_language": "en",
                "target_language": "pt-BR",
                "level": "B1",
            }
        )
        return result, provider

    def test_analyzes_a_contextualized_word(self) -> None:
        result, provider = self.analyze()

        self.assertEqual(result["analysis"], VALID_ANALYSIS)
        self.assertEqual(
            result["metadata"], {"model": "gemini-3.5-flash-lite", "prompt_version": PROMPT_VERSION}
        )
        self.assertIn('"selected_term":"run"', provider.calls[0]["prompt"])

    def test_asks_gemini_only_for_what_the_serializer_accepts(self) -> None:
        _, provider = self.analyze()

        self.assertCountEqual(provider.calls[0]["schema"]["required"], VALID_ANALYSIS)

    def test_rejects_an_invalid_provider_response(self) -> None:
        invalid = {**VALID_ANALYSIS, "explanation": "", "unexpected": "value"}

        with self.assertRaises(GeminiInvalidResponseError):
            self.analyze(invalid)

    def test_rejects_a_response_without_the_card_fields(self) -> None:
        for field, value in (
            ("formality", "casual"),
            ("contexts", None),
            ("phonetic", ""),
            ("literal", ""),
            ("dialogue", [{"speaker": "A", "text": "Hi.", "translation": "Oi."}]),
            ("dialogue", [{"speaker": "C", "text": "Hi.", "translation": "Oi."}] * 2),
        ):
            with self.subTest(field=field), self.assertRaises(GeminiInvalidResponseError):
                self.analyze({**VALID_ANALYSIS, field: value})
