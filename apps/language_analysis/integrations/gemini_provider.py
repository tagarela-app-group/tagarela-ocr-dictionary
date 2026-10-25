import json
from typing import Any

import httpx
from django.conf import settings
from google import genai
from rest_framework import status
from rest_framework.exceptions import APIException

from apps.language_analysis.prompts.linguistic_analysis import SYSTEM_PROMPT
from apps.language_analysis.serializers import FORMALITY_LEVELS


class GeminiConfigurationError(APIException):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_detail = "Language analysis is unavailable."
    default_code = "language_analysis_unavailable"


class GeminiUnavailableError(APIException):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_detail = "Language analysis is temporarily unavailable."
    default_code = "language_analysis_unavailable"


class GeminiTimeoutError(APIException):
    status_code = status.HTTP_504_GATEWAY_TIMEOUT
    default_detail = "Language analysis timed out."
    default_code = "language_analysis_timeout"


class GeminiInvalidResponseError(APIException):
    status_code = status.HTTP_502_BAD_GATEWAY
    default_detail = "Language analysis returned an invalid response."
    default_code = "language_analysis_invalid_response"


ANALYSIS_RESPONSE_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "focus",
        "detected_language",
        "translation",
        "meaning_in_context",
        "explanation",
        "part_of_speech",
        "is_ambiguous",
        "alternative_meanings",
        "examples",
        "usage_notes",
        "phonetic",
        "source_definition",
        "source_meaning_in_context",
        "source_explanation",
        "pitfall",
        "collocations",
        "synonyms",
        "antonyms",
        "formality",
        "formality_note",
        "contexts",
    ],
    "properties": {
        "focus": {"type": "string"},
        "detected_language": {"type": "string"},
        "translation": {"type": ["string", "null"]},
        "meaning_in_context": {"type": ["string", "null"]},
        "explanation": {"type": "string"},
        "part_of_speech": {"type": ["string", "null"]},
        "is_ambiguous": {"type": "boolean"},
        "alternative_meanings": {
            "type": "array",
            "maxItems": 3,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["meaning", "usage_context", "example", "translation"],
                "properties": {
                    "meaning": {"type": "string"},
                    "usage_context": {"type": "string"},
                    "example": {"type": "string"},
                    "translation": {"type": "string"},
                },
            },
        },
        "examples": {
            "type": "array",
            "maxItems": 3,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["original", "translation", "usage_context"],
                "properties": {
                    "original": {"type": "string"},
                    "translation": {"type": "string"},
                    "usage_context": {"type": "string"},
                },
            },
        },
        "usage_notes": {"type": "array", "maxItems": 5, "items": {"type": "string"}},
        "phonetic": {"type": ["string", "null"]},
        "source_definition": {"type": ["string", "null"]},
        "source_meaning_in_context": {"type": ["string", "null"]},
        "source_explanation": {"type": "string"},
        "pitfall": {"type": ["string", "null"]},
        "collocations": {"type": "array", "maxItems": 6, "items": {"type": "string"}},
        "synonyms": {"type": "array", "maxItems": 5, "items": {"type": "string"}},
        "antonyms": {"type": "array", "maxItems": 5, "items": {"type": "string"}},
        "formality": {"type": "string", "enum": list(FORMALITY_LEVELS)},
        "formality_note": {"type": ["string", "null"]},
        "contexts": {
            "type": "array",
            "maxItems": 4,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["context", "fits", "alternative"],
                "properties": {
                    "context": {"type": "string"},
                    "fits": {"type": "boolean"},
                    "alternative": {"type": ["string", "null"]},
                },
            },
        },
    },
}


class GeminiProvider:
    def __init__(self, client: Any | None = None) -> None:
        self.client = client

    def analyze(self, prompt: str) -> dict[str, Any]:
        if not settings.GEMINI_API_KEY:
            raise GeminiConfigurationError

        try:
            interaction = self._client().interactions.create(
                model=settings.GEMINI_MODEL,
                input=prompt,
                system_instruction=SYSTEM_PROMPT,
                response_format={
                    "type": "text",
                    "mime_type": "application/json",
                    "schema": ANALYSIS_RESPONSE_SCHEMA,
                },
                store=False,
            )
        except (TimeoutError, httpx.TimeoutException) as error:
            raise GeminiTimeoutError from error
        except APIException:
            raise
        except Exception as error:
            raise GeminiUnavailableError from error

        try:
            output = interaction.output_text
            if not isinstance(output, str) or not output.strip():
                raise ValueError
            result = json.loads(output)
        except (AttributeError, TypeError, ValueError, json.JSONDecodeError) as error:
            raise GeminiInvalidResponseError from error

        if not isinstance(result, dict):
            raise GeminiInvalidResponseError

        return result

    def _client(self) -> Any:
        if self.client is None:
            self.client = genai.Client(
                api_key=settings.GEMINI_API_KEY,
                http_options={"timeout": settings.GEMINI_TIMEOUT * 1000},
            )
        return self.client
