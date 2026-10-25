from typing import Any

from django.conf import settings

from apps.language_analysis.integrations.gemini_provider import (
    GeminiInvalidResponseError,
    GeminiProvider,
)
from apps.language_analysis.prompts.linguistic_analysis import PROMPT_VERSION, build_analysis_input
from apps.language_analysis.serializers import (
    LanguageAnalysisResponseSerializer,
    LinguisticAnalysisSerializer,
)


class LinguisticAnalysisService:
    def __init__(self, provider: GeminiProvider | None = None):
        self.provider = provider or GeminiProvider()

    def analyze(self, data: dict[str, Any]) -> dict[str, Any]:
        input_data = {
            "text": data["text"],
            "selected_term": data.get("selected_term"),
            "source_language": data["source_language"],
            "target_language": data["target_language"],
            "level": data.get("level"),
        }
        analysis = LinguisticAnalysisSerializer(
            data=self.provider.analyze(build_analysis_input(input_data))
        )
        if not analysis.is_valid():
            raise GeminiInvalidResponseError

        response = {
            "input": input_data,
            "analysis": analysis.validated_data,
            "metadata": {"model": settings.GEMINI_MODEL, "prompt_version": PROMPT_VERSION},
        }
        serializer = LanguageAnalysisResponseSerializer(data=response)
        if not serializer.is_valid():
            raise GeminiInvalidResponseError

        return serializer.validated_data
