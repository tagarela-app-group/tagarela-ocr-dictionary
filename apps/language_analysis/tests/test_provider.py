import json
from types import SimpleNamespace
from unittest.mock import ANY, Mock, patch

import httpx
from django.test import SimpleTestCase, override_settings

from apps.language_analysis.integrations.gemini_provider import (
    ANALYSIS_RESPONSE_SCHEMA,
    GeminiConfigurationError,
    GeminiInvalidResponseError,
    GeminiProvider,
    GeminiTimeoutError,
    GeminiUnavailableError,
)
from apps.language_analysis.tests.helpers import VALID_ANALYSIS


class GeminiProviderTests(SimpleTestCase):
    @override_settings(GEMINI_API_KEY="")
    def test_requires_an_api_key(self):
        with self.assertRaises(GeminiConfigurationError):
            GeminiProvider().analyze("prompt")

    @override_settings(GEMINI_API_KEY="key", GEMINI_MODEL="configured-model", GEMINI_TIMEOUT=17)
    @patch("apps.language_analysis.integrations.gemini_provider.genai.Client")
    def test_requests_a_stateless_structured_interaction(self, client_class):
        interaction = SimpleNamespace(output_text=json.dumps(VALID_ANALYSIS))
        client_class.return_value.interactions.create.return_value = interaction

        result = GeminiProvider().analyze("prompt")

        self.assertEqual(result, VALID_ANALYSIS)
        client_class.assert_called_once_with(api_key="key", http_options={"timeout": 17000})
        client_class.return_value.interactions.create.assert_called_once_with(
            model="configured-model",
            input="prompt",
            system_instruction=ANY,
            response_format={
                "type": "text",
                "mime_type": "application/json",
                "schema": ANALYSIS_RESPONSE_SCHEMA,
            },
            store=False,
        )

    @override_settings(GEMINI_API_KEY="key")
    def test_rejects_an_invalid_json_response(self):
        client = Mock()
        client.interactions.create.return_value = SimpleNamespace(output_text="not json")

        with self.assertRaises(GeminiInvalidResponseError):
            GeminiProvider(client).analyze("prompt")

    @override_settings(GEMINI_API_KEY="key")
    def test_maps_timeouts_to_gateway_timeout(self):
        client = Mock()
        client.interactions.create.side_effect = httpx.TimeoutException("timeout")

        with self.assertRaises(GeminiTimeoutError):
            GeminiProvider(client).analyze("prompt")

    @override_settings(GEMINI_API_KEY="key")
    def test_maps_provider_failures_to_service_unavailable(self):
        client = Mock()
        client.interactions.create.side_effect = RuntimeError("provider failed")

        with self.assertRaises(GeminiUnavailableError):
            GeminiProvider(client).analyze("prompt")
