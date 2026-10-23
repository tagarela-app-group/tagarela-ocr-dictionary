from unittest.mock import patch

import httpx
from django.test import SimpleTestCase, override_settings

from apps.lexical.providers.dictionary import DictionaryProvider

PAYLOAD = [
    {
        "word": "fox",
        "meanings": [
            {
                "partOfSpeech": "noun",
                "definitions": [{"definition": "A small wild canine."}, {"definition": ""}],
            },
            {"partOfSpeech": "verb", "definitions": [{"definition": "To trick."}]},
        ],
    },
    {"word": "fox", "meanings": [{"definitions": [{"definition": "A clever person."}]}]},
]


@override_settings(
    DICTIONARY_API_BASE_URL="https://dicionario.test/entries",
    DICTIONARY_API_TIMEOUT_SECONDS=2,
)
class DictionaryProviderTests(SimpleTestCase):
    def fetch(self, word: str = "fox", response=None, error=None):
        with patch("apps.lexical.providers.dictionary.httpx.get") as get:
            get.return_value = response
            get.side_effect = error
            result = DictionaryProvider().fetch(word, "en")

        return result, get

    def test_returns_every_definition_in_order(self):
        result, get = self.fetch(response=httpx.Response(200, json=PAYLOAD))

        self.assertEqual(
            result,
            {
                "word": "fox",
                "definitions": ["A small wild canine.", "To trick.", "A clever person."],
            },
        )
        get.assert_called_once_with("https://dicionario.test/entries/en/fox", timeout=2)

    def test_quotes_word_in_url(self):
        _, get = self.fetch("pão de", httpx.Response(200, json=PAYLOAD))

        self.assertEqual(get.call_args.args[0], "https://dicionario.test/entries/en/p%C3%A3o%20de")

    def test_error_status_returns_none(self):
        for status_code in [404, 500]:
            with self.subTest(status_code):
                result, _ = self.fetch(response=httpx.Response(status_code, json={"title": "x"}))

                self.assertIsNone(result)

    def test_network_error_returns_none(self):
        for error in [httpx.ConnectError("down"), httpx.ReadTimeout("slow")]:
            with self.subTest(type(error).__name__):
                result, _ = self.fetch(error=error)

                self.assertIsNone(result)

    def test_payload_without_definitions_returns_none(self):
        for payload in [{}, [], [{"meanings": []}], [{"meanings": [{"definitions": []}]}]]:
            with self.subTest(payload):
                result, _ = self.fetch(response=httpx.Response(200, json=payload))

                self.assertIsNone(result)
