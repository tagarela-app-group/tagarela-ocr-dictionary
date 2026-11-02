from django.test import SimpleTestCase, override_settings

from apps.exercises.kinds import KINDS, Effort
from apps.exercises.kinds.listen_write import ListenWrite, syllables
from apps.exercises.kinds.reply import Reply
from apps.exercises.models import Exercise
from apps.exercises.tests.helpers import FENCE_ITEMS, REPLY_ITEMS


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


class ReplyTests(SimpleTestCase):
    USE, UNDERSTAND, AUDIO = REPLY_ITEMS

    def test_finds_the_answer_inside_the_reply(self):
        payload = Reply().to_payload(self.USE)

        self.assertEqual(payload["mode"], "use")
        self.assertEqual(payload["reply"][payload["start"] : payload["end"]], "on the fence")
        self.assertEqual(payload["wrong"], [])
        self.assertEqual(payload["extra"]["say"], "on the fence about")

    def test_understand_keeps_its_wrong_phrases(self):
        payload = Reply().to_payload(self.UNDERSTAND)

        self.assertEqual(payload["reply"][payload["start"] : payload["end"]], "haven't decided yet")
        self.assertEqual(len(payload["wrong"]), 3)

    def test_rejects_an_answer_missing_from_the_reply(self):
        self.assertIsNone(Reply().to_payload({**self.USE, "source_answer": "up in the air"}))

    def test_rejects_nina_giving_away_the_focus(self):
        giveaway = {**self.USE, "source_nina": "Are you still on the fence?"}

        self.assertIsNone(Reply().to_payload(giveaway))
        self.assertIsNone(Reply().to_payload({**self.AUDIO, **giveaway, "mode": "audio"}))

    def test_understand_needs_the_focus_marked_in_ninas_message(self):
        self.assertIsNone(
            Reply().to_payload({**self.UNDERSTAND, "source_nina": "I'm on the fence about it."})
        )

    def test_understand_rejects_repeated_or_missing_wrong_phrases(self):
        for wrong in (
            {"source_wrong_1": ""},
            {"source_wrong_1": "Felt Embarrassed", "source_wrong_2": "felt embarrassed"},
            {"source_wrong_1": "haven't decided yet"},
        ):
            self.assertIsNone(Reply().to_payload({**self.UNDERSTAND, **wrong}))

    def test_audio_is_worth_listening_and_the_rest_reading(self):
        reply = Reply()

        self.assertEqual(reply.effort_of({"mode": "audio"}), Effort.LISTEN)
        self.assertEqual(reply.effort_of({"mode": "use"}), Effort.READ)
        self.assertEqual(reply.effort_of(None), Effort.READ)

    def test_needs_four_read_terms(self):
        self.assertFalse(Reply().available(3))
        self.assertTrue(Reply().available(4))

    @override_settings(REVIEW_REPLY_MIN_INTERVAL_DAYS=4)
    def test_stays_out_of_new_terms_and_retests(self):
        self.assertFalse(Reply().fits(3.9, retest=False))
        self.assertTrue(Reply().fits(4, retest=False))
        self.assertFalse(Reply().fits(32, retest=True))


class SyllablesTests(SimpleTestCase):
    def test_keeps_breaks_inside_words_only(self):
        self.assertEqual(
            syllables("count your chickens", "count| your chick|ens|"), ("count your chick|ens")
        )

    def test_falls_back_to_the_answer_when_the_letters_differ(self):
        self.assertEqual(syllables("chickens", "chick|en"), "chickens")
