import re
import unicodedata

from django.conf import settings

from apps.lexical.cache import LexicalCache
from apps.lexical.models import LexicalEntry
from apps.lexical.providers.dictionary import DictionaryProvider


class LexicalPreparationService:
    def extract_words(self, text: str) -> list[str]:
        words = [self.normalize_word(word) for word in re.findall(r"\b[\w'-]+\b", text)]
        unique_words = {word for word in words if word}

        return sorted(unique_words)

    def normalize_word(self, word: str) -> str:
        normalized = unicodedata.normalize("NFKC", word)

        return normalized.casefold().strip("-'")


class LexicalLookupService:
    def __init__(
        self,
        cache: LexicalCache | None = None,
        dictionary_provider: DictionaryProvider | None = None,
        preparation_service: LexicalPreparationService | None = None,
    ) -> None:
        self.cache = cache or LexicalCache()
        self.dictionary_provider = dictionary_provider or DictionaryProvider()
        self.preparation_service = preparation_service or LexicalPreparationService()

    def analyze_text(self, text: str, language: str | None = None) -> list[dict]:
        language = language or settings.LEXICAL_LANGUAGE
        words = self.preparation_service.extract_words(text)

        if not words:
            return []

        cached_entries = self.cache.get_many(words, language)
        missing_from_cache = [word for word in words if word not in cached_entries]

        database_entries = self._get_database_entries(missing_from_cache, language)
        missing_from_database = [
            word for word in missing_from_cache if word not in database_entries
        ]

        dictionary_entries = self._get_dictionary_entries(missing_from_database, language)

        if database_entries:
            self.cache.set_many(list(database_entries.values()), language)

        if dictionary_entries:
            self._save_dictionary_entries(dictionary_entries, language)
            self.cache.set_many(list(dictionary_entries.values()), language)

        return [
            self._entry_for_response(word, cached_entries, database_entries, dictionary_entries)
            for word in words
        ]

    def _get_database_entries(self, words: list[str], language: str) -> dict[str, dict]:
        if not words:
            return {}

        entries = LexicalEntry.objects.filter(
            language=language,
            normalized_word__in=words,
        )

        return {
            entry.normalized_word: {
                "word": entry.normalized_word,
                "definitions": entry.data.get("definitions", []),
                "source": "database",
            }
            for entry in entries
        }

    def _get_dictionary_entries(self, words: list[str], language: str) -> dict[str, dict]:
        entries = {}

        for word in words:
            data = self.dictionary_provider.fetch(word, language)
            definitions = data["definitions"] if data else []

            entries[word] = {
                "word": word,
                "definitions": definitions,
                "source": "dictionary",
            }

        return entries

    def _save_dictionary_entries(self, entries: dict[str, dict], language: str) -> None:
        lexical_entries = [
            LexicalEntry(
                word=entry["word"],
                normalized_word=word,
                language=language,
                data={"definitions": entry["definitions"]},
                source="dictionary",
            )
            for word, entry in entries.items()
        ]

        LexicalEntry.objects.bulk_create(
            lexical_entries,
            update_conflicts=True,
            update_fields=["word", "data", "source", "updated_at"],
            unique_fields=["normalized_word", "language"],
        )

    def _entry_for_response(
        self,
        word: str,
        cached_entries: dict[str, dict],
        database_entries: dict[str, dict],
        dictionary_entries: dict[str, dict],
    ) -> dict:
        if word in cached_entries:
            return {**cached_entries[word], "source": "cache"}

        if word in database_entries:
            return database_entries[word]

        return dictionary_entries[word]
