from types import SimpleNamespace
from unittest.mock import Mock

import httpx
from django.test import SimpleTestCase, override_settings

from apps.language_analysis.providers.gemini import (
    GeminiConfigurationError,
    GeminiInvalidResponseError,
    GeminiProvider,
    GeminiTimeoutError,
    GeminiUnavailableError,
)


def generate(client: Mock | None = None) -> dict[str, object]:
    return GeminiProvider(client).generate("prompt", system_instruction="rules", schema={})


@override_settings(GEMINI_API_KEY="key")
class GeminiProviderTests(SimpleTestCase):
    @override_settings(GEMINI_API_KEY="")
    def test_requires_an_api_key(self) -> None:
        with self.assertRaises(GeminiConfigurationError):
            generate()

    def test_never_stores_the_interaction(self) -> None:
        client = Mock()
        client.interactions.create.return_value = SimpleNamespace(output_text='{"items": []}')

        self.assertEqual(generate(client), {"items": []})
        self.assertIs(client.interactions.create.call_args.kwargs["store"], False)

    def test_rejects_output_that_is_not_a_json_object(self) -> None:
        for output in ("not json", "[]", "", None):
            with self.subTest(output=output):
                client = Mock()
                client.interactions.create.return_value = SimpleNamespace(output_text=output)

                with self.assertRaises(GeminiInvalidResponseError):
                    generate(client)

    def test_maps_timeouts_to_gateway_timeout(self) -> None:
        client = Mock()
        client.interactions.create.side_effect = httpx.TimeoutException("timeout")

        with self.assertRaises(GeminiTimeoutError):
            generate(client)

    def test_maps_provider_failures_to_service_unavailable(self) -> None:
        client = Mock()
        client.interactions.create.side_effect = RuntimeError("provider failed")

        with self.assertRaises(GeminiUnavailableError):
            generate(client)
