from django.test import SimpleTestCase, TestCase, override_settings

from apps.lexical.models import LexicalEntry
from apps.lexical.services import LexicalLookupService, LexicalPreparationService


class FakeCache:
    def __init__(self) -> None:
        self.entries: dict[tuple[str, str], dict] = {}

    def get_many(self, words: list[str], language: str) -> dict[str, dict]:
        return {
            word: self.entries[(language, word)]
            for word in words
            if (language, word) in self.entries
        }

    def set_many(self, entries: list[dict], language: str) -> None:
        for entry in entries:
            self.entries[(language, entry["word"])] = entry


class FakeDictionaryProvider:
    def __init__(self) -> None:
        self.results: dict[str, dict] = {}
        self.calls: list[tuple[str, str]] = []

    def fetch(self, word: str, language: str) -> dict | None:
        self.calls.append((word, language))
        return self.results.get(word)


class LexicalPreparationServiceTests(SimpleTestCase):
    def extract(self, text: str) -> list[str]:
        return LexicalPreparationService().extract_words(text)

    def test_returns_unique_casefolded_words_in_order(self):
        self.assertEqual(
            self.extract("The quick brown fox. THE FOX!"), ["brown", "fox", "quick", "the"]
        )

    def test_keeps_inner_hyphen_and_apostrophe_only(self):
        self.assertEqual(
            self.extract("'hello' -world- don't well-known"),
            ["don't", "hello", "well-known", "world"],
        )

    def test_normalizes_unicode_with_nfkc(self):
        self.assertEqual(self.extract("ﬁne Ａｐｐｌｅ"), ["apple", "fine"])

    def test_numbers_are_words(self):
        self.assertEqual(self.extract("2 cats"), ["2", "cats"])

    def test_text_without_words_returns_empty(self):
        for text in ["", "  ", "!!! ..."]:
            with self.subTest(text):
                self.assertEqual(self.extract(text), [])


@override_settings(LEXICAL_LANGUAGE="en")
class LexicalLookupServiceTests(TestCase):
    def setUp(self):
        self.cache = FakeCache()
        self.dictionary = FakeDictionaryProvider()
        self.service = LexicalLookupService(cache=self.cache, dictionary_provider=self.dictionary)

    def create_entry(self, word: str, definitions: list[str], language: str = "en"):
        return LexicalEntry.objects.create(
            word=word,
            normalized_word=word,
            language=language,
            data={"definitions": definitions},
            source="dictionary",
        )

    def test_text_without_words_skips_lookup(self):
        self.assertEqual(self.service.analyze_text("!!!"), [])
        self.assertEqual(self.dictionary.calls, [])

    def test_cache_hit_returns_cache_source(self):
        self.cache.entries[("en", "fox")] = {
            "word": "fox",
            "definitions": ["A canine."],
            "source": "dictionary",
        }

        result = self.service.analyze_text("Fox")

        self.assertEqual(result, [{"word": "fox", "definitions": ["A canine."], "source": "cache"}])
        self.assertEqual(self.dictionary.calls, [])

    def test_database_hit_returns_database_source_and_fills_cache(self):
        self.create_entry("fox", ["A canine."])
        expected = {"word": "fox", "definitions": ["A canine."], "source": "database"}

        result = self.service.analyze_text("fox")

        self.assertEqual(result, [expected])
        self.assertEqual(self.cache.entries[("en", "fox")], expected)
        self.assertEqual(self.dictionary.calls, [])

    def test_dictionary_hit_saves_database_and_cache(self):
        self.dictionary.results["fox"] = {"word": "fox", "definitions": ["A canine."]}
        expected = {"word": "fox", "definitions": ["A canine."], "source": "dictionary"}

        result = self.service.analyze_text("fox")

        self.assertEqual(result, [expected])
        entry = LexicalEntry.objects.get(normalized_word="fox", language="en")
        self.assertEqual(entry.data, {"definitions": ["A canine."]})
        self.assertEqual(entry.source, "dictionary")
        self.assertEqual(self.cache.entries[("en", "fox")], expected)

    def test_dictionary_without_definition_saves_empty_definitions(self):
        result = self.service.analyze_text("zzzx")

        self.assertEqual(result, [{"word": "zzzx", "definitions": [], "source": "dictionary"}])
        entry = LexicalEntry.objects.get(normalized_word="zzzx", language="en")
        self.assertEqual(entry.data, {"definitions": []})

    def test_each_word_uses_first_source_found_in_order(self):
        self.cache.entries[("en", "cat")] = {
            "word": "cat",
            "definitions": [],
            "source": "dictionary",
        }
        self.create_entry("dog", ["A pet."])
        self.dictionary.results["fox"] = {"word": "fox", "definitions": ["A canine."]}

        result = self.service.analyze_text("fox dog cat")

        self.assertEqual(
            [(item["word"], item["source"]) for item in result],
            [("cat", "cache"), ("dog", "database"), ("fox", "dictionary")],
        )
        self.assertEqual(self.dictionary.calls, [("fox", "en")])

    def test_language_argument_isolates_cache_database_and_dictionary(self):
        self.create_entry("fox", ["A canine."], language="en")

        result = self.service.analyze_text("fox", language="pt")

        self.assertEqual(result[0]["source"], "dictionary")
        self.assertEqual(self.dictionary.calls, [("fox", "pt")])
        self.assertTrue(LexicalEntry.objects.filter(normalized_word="fox", language="pt").exists())
        self.assertIn(("pt", "fox"), self.cache.entries)
