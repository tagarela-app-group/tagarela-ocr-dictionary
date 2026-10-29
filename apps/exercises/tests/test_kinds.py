from django.test import SimpleTestCase

from apps.exercises.kinds import KINDS
from apps.exercises.kinds.listen_write import ListenWrite, syllables
from apps.exercises.models import Exercise
from apps.exercises.tests.helpers import FENCE_ITEMS


def item(**fields: str) -> dict[str, str]:
    return {**FENCE_ITEMS[0], **fields}


class RegistryTests(SimpleTestCase):
    def test_every_kind_has_a_generator(self):
        self.assertEqual(set(KINDS), set(Exercise.Kind.values))


class ListenWriteTests(SimpleTestCase):
    def test_finds_the_answer_inside_the_sentence(self):
        payload = ListenWrite().to_payload(item())

        self.assertEqual(
            payload,
            {
                "sentence": "I'm still on the fence about moving to Lisbon.",
                "start": 10,
                "end": 22,
                "syllables": "on the fence",
                "translation": "Ainda tô em cima do muro sobre me mudar pra Lisboa.",
                "extra": {
                    "note": "Depois vem *about*: *on the fence about* alguma coisa.",
                    "say": "on the fence about",
                },
            },
        )

    def test_copies_the_casing_from_the_sentence_and_cleans_spaces(self):
        payload = ListenWrite().to_payload(
            item(
                source_sentence="Procrastination  is why I'm   up at 3 a.m.",
                source_answer="procrastination",
                source_syllables="pro|cras|ti|na|tion",
            )
        )

        self.assertEqual(payload["sentence"], "Procrastination is why I'm up at 3 a.m.")
        self.assertEqual((payload["start"], payload["end"]), (0, 15))
        self.assertEqual(payload["syllables"], "Pro|cras|ti|na|tion")

    def test_rejects_an_answer_missing_from_the_sentence(self):
        self.assertIsNone(ListenWrite().to_payload(item(source_answer="up in the air")))

    def test_rejects_an_answer_inside_another_word(self):
        self.assertIsNone(
            ListenWrite().to_payload(
                item(source_sentence="The fences are tall.", source_answer="fence")
            )
        )

    def test_rejects_an_answer_without_letters(self):
        self.assertIsNone(
            ListenWrite().to_payload(item(source_sentence="It costs 30 now.", source_answer="30"))
        )

    def test_drops_invalid_and_repeated_items(self):
        response = {
            "items": [FENCE_ITEMS[0], {"source_sentence": "x"}, FENCE_ITEMS[0], FENCE_ITEMS[1]]
        }

        payloads = ListenWrite().payloads(response)

        self.assertEqual(
            [p["sentence"] for p in payloads],
            [
                FENCE_ITEMS[0]["source_sentence"],
                FENCE_ITEMS[1]["source_sentence"],
            ],
        )

    def test_ignores_a_response_without_items(self):
        self.assertEqual(ListenWrite().payloads({"items": "nope"}), [])


class SyllablesTests(SimpleTestCase):
    def test_keeps_breaks_inside_words_only(self):
        self.assertEqual(
            syllables("count your chickens", "count| your chick|ens|"), ("count your chick|ens")
        )

    def test_falls_back_to_the_answer_when_the_letters_differ(self):
        self.assertEqual(syllables("chickens", "chick|en"), "chickens")
