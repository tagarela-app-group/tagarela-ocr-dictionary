from typing import Any

from django.conf import settings

from apps.language_analysis.integrations.gemini_provider import (
    GeminiInvalidResponseError,
    GeminiProvider,
)
from apps.language_analysis.prompts.linguistic_analysis import PROMPT_VERSION, build_analysis_input
from apps.language_analysis.serializers import LinguisticAnalysisSerializer


class LinguisticAnalysisService:
    def __init__(self, provider: GeminiProvider | None = None):
        self.provider = provider or GeminiProvider()

    def analyze(self, data: dict[str, Any]) -> dict[str, Any]:
        analysis = LinguisticAnalysisSerializer(
            data=self.provider.analyze(build_analysis_input(data))
        )
        if not analysis.is_valid():
            raise GeminiInvalidResponseError

        return {
            "analysis": analysis.validated_data,
            "metadata": {"model": settings.GEMINI_MODEL, "prompt_version": PROMPT_VERSION},
        }
