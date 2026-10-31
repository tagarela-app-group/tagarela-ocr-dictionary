from typing import TypedDict

from django.conf import settings

from apps.common.schema import json_schema
from apps.language_analysis.prompts import PROMPT_VERSION, SYSTEM_PROMPT, build_analysis_input
from apps.language_analysis.providers.gemini import GeminiInvalidResponseError, GeminiProvider
from apps.language_analysis.serializers import LinguisticAnalysisSerializer

ANALYSIS_SCHEMA = json_schema(LinguisticAnalysisSerializer())


class AnalysisInput(TypedDict):
    text: str
    selected_term: str | None
    source_language: str
    target_language: str
    level: str | None


class AnalysisMetadata(TypedDict):
    model: str
    prompt_version: str


class AnalysisResult(TypedDict):
    analysis: dict[str, object]
    metadata: AnalysisMetadata


class LinguisticAnalysisService:
    def __init__(self, provider: GeminiProvider | None = None):
        self.provider = provider or GeminiProvider()

    def analyze(self, data: AnalysisInput) -> AnalysisResult:
        analysis = LinguisticAnalysisSerializer(
            data=self.provider.generate(
                build_analysis_input(data),
                system_instruction=SYSTEM_PROMPT,
                schema=ANALYSIS_SCHEMA,
            )
        )
        if not analysis.is_valid():
            raise GeminiInvalidResponseError

        return {
            "analysis": analysis.validated_data,
            "metadata": {"model": settings.GEMINI_MODEL, "prompt_version": PROMPT_VERSION},
        }
