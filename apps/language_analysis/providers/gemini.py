import json
from collections.abc import Mapping

import httpx
from django.conf import settings
from google import genai
from rest_framework import status
from rest_framework.exceptions import APIException


class GeminiConfigurationError(APIException):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_detail = "A análise não está disponível."
    default_code = "language_analysis_unavailable"


class GeminiUnavailableError(APIException):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_detail = "A análise está fora do ar. Tente de novo em instantes."
    default_code = "language_analysis_unavailable"


class GeminiTimeoutError(APIException):
    status_code = status.HTTP_504_GATEWAY_TIMEOUT
    default_detail = "A análise demorou demais. Tente de novo."
    default_code = "language_analysis_timeout"


class GeminiInvalidResponseError(APIException):
    status_code = status.HTTP_502_BAD_GATEWAY
    default_detail = "A análise voltou com uma resposta inválida."
    default_code = "language_analysis_invalid_response"


class GeminiProvider:
    def __init__(self, client: genai.Client | None = None) -> None:
        self.client = client

    def generate(
        self, prompt: str, *, system_instruction: str, schema: Mapping[str, object]
    ) -> dict[str, object]:
        if not settings.GEMINI_API_KEY:
            raise GeminiConfigurationError

        try:
            interaction = self._client().interactions.create(
                model=settings.GEMINI_MODEL,
                input=prompt,
                system_instruction=system_instruction,
                response_format={
                    "type": "text",
                    "mime_type": "application/json",
                    "schema": schema,
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

    def _client(self) -> genai.Client:
        if self.client is None:
            self.client = genai.Client(
                api_key=settings.GEMINI_API_KEY,
                http_options={"timeout": settings.GEMINI_TIMEOUT * 1000},
            )
        return self.client
