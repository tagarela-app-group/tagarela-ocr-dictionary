from urllib.parse import quote

import httpx
from django.conf import settings


class DictionaryProvider:
    def fetch(self, word: str, language: str) -> dict | None:
        url = f"{settings.DICTIONARY_API_BASE_URL}/{quote(language)}/{quote(word)}"

        try:
            response = httpx.get(url, timeout=settings.DICTIONARY_API_TIMEOUT_SECONDS)
        except httpx.HTTPError:
            return None

        if response.status_code >= 400:
            return None

        return self._parse_response(word, response.json())

    def _parse_response(self, word: str, payload) -> dict | None:
        if not isinstance(payload, list) or not payload:
            return None

        definitions = []

        for entry in payload:
            for meaning in entry.get("meanings", []):
                for definition in meaning.get("definitions", []):
                    text = definition.get("definition")
                    if text:
                        definitions.append(text)

        if not definitions:
            return None

        return {
            "word": word,
            "definitions": definitions,
        }
