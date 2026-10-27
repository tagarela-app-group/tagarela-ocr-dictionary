from datetime import timedelta
from unittest.mock import patch

from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APITestCase

from apps.captures.models import Capture, CaptureTerm
from apps.captures.tests.helpers import make_capture, make_user
from apps.cards.models import TermCard
from apps.courses.tests.helpers import make_course
from apps.language_analysis.integrations.gemini_provider import GeminiUnavailableError
from apps.language_analysis.tests.helpers import VALID_ANALYSIS
from apps.vocabulary.models import Term
from apps.vocabulary.tests.helpers import make_group, make_term

TEXT = "Honestly, I'm on the fence about it. Let me sleep on it."
METADATA = {"model": "gemini-3.5-flash-lite", "prompt_version": "2.5"}


class StubAnalysis:
    def __init__(self, error=None):
        self.calls = []
        self.error = error
        self.analysis = VALID_ANALYSIS

    def analyze(self, data):
        self.calls.append(data)
        if self.error:
            raise self.error
        return {"input": data, "analysis": self.analysis, "metadata": METADATA}


class TermCardApiTestCase(APITestCase):
    def setUp(self):
        super().setUp()
        self.user = make_user()
        self.client.force_authenticate(self.user)
        self.course = make_course(self.user)
        self.analysis = StubAnalysis()
        service = patch("apps.cards.services.LinguisticAnalysisService", return_value=self.analysis)
        service.start()
        self.addCleanup(service.stop)

    def url(self, term) -> str:
        return f"/api/v1/terms/{term.id}"

    def analyzed(self, text=TEXT, days_ago=0, **fields):
        return make_capture(
            self.user,
            text=text,
            original_text=text,
            status=Capture.Status.ANALYZED,
            analyzed_at=timezone.now(),
            captured_at=timezone.now() - timedelta(days=days_ago),
            **fields,
        )

    def mark(self, capture, text):
        start = capture.text.index(text)
        return CaptureTerm.objects.create(
            capture=capture, text=text, start=start, end=start + len(text)
        )


class TermDetailTests(TermCardApiTestCase):
    def test_first_open_builds_the_card_from_the_capture(self):
        fence = make_term(self.user, "on the fence", make_group(self.user))
        sleep = make_term(self.user, "sleep on it")
        capture = self.analyzed()
        self.mark(capture, "on the fence")
        self.mark(capture, "sleep on it")
        self.mark(capture, "Honestly")

        response = self.client.get(self.url(fence))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            self.analysis.calls,
            [
                {
                    "text": TEXT,
                    "selected_term": "on the fence",
                    "source_language": "en",
                    "target_language": "pt-BR",
                    "level": None,
                }
            ],
        )
        body = response.json()
        self.assertEqual(body["id"], str(fence.id))
        self.assertEqual(body["translation"], "administrar")
        self.assertEqual(body["group"]["name"], "Viagem")
        self.assertFalse(body["revealed"])
        self.assertEqual(
            body["captures"][0]["terms"],
            [
                {"text": "Honestly", "start": 0, "end": 8, "term": None},
                {"text": "on the fence", "start": 14, "end": 26, "term": str(fence.id)},
                {"text": "sleep on it", "start": 44, "end": 55, "term": str(sleep.id)},
            ],
        )
        fence.refresh_from_db()
        self.assertEqual(fence.translation, "administrar")
        self.assertEqual(TermCard.objects.get().prompt_version, "2.5")

    def test_card_speaks_learning_and_base_languages(self):
        term = make_term(self.user, "run")

        card = self.client.get(self.url(term)).json()["card"]

        self.assertEqual(
            card,
            {
                "phonetic": "/rʌn/",
                "learning": {
                    "definition": "to manage or operate",
                    "in_context": "To manage a small business.",
                    "explanation": "Run is often used for being in charge of a company.",
                    "pitfall": "Run a business is not about speed.",
                    "imagine": "Someone behind the counter, taking care of their own shop.",
                },
                "base": {
                    "translation": "administrar",
                    "in_context": "Manage a business.",
                    "explanation": "Here, run means manage rather than move quickly.",
                    "pitfall": "Não traduza como correr quando o assunto é uma empresa.",
                    "literal": None,
                    "imagine": "Alguém no balcão, cuidando de tudo na própria loja.",
                    "formality_note": "Tranquilo numa conversa e no trabalho.",
                    "fits": [
                        {"context": "Reunião de trabalho", "fits": True, "alternative": None},
                        {"context": "Contrato", "fits": False, "alternative": "operate"},
                    ],
                },
                "mistake": None,
                "examples": [
                    {
                        "text": "She runs a restaurant.",
                        "translation": "Ela administra um restaurante.",
                    }
                ],
                "collocations": ["run a business", "run the show"],
                "synonyms": ["manage", "operate"],
                "antonyms": [],
                "formality": "neutral",
                "formality_note": "Fine in conversation and at work.",
                "fits": [
                    {"context": "Work meeting", "fits": True, "alternative": None},
                    {"context": "Contract", "fits": False, "alternative": "operate"},
                ],
                "dialogue": [
                    {
                        "speaker": "A",
                        "text": "What does your aunt do?",
                        "translation": "O que sua tia faz?",
                    },
                    {
                        "speaker": "B",
                        "text": "She runs a bakery downtown.",
                        "translation": "Ela administra uma padaria no centro.",
                    },
                ],
            },
        )

    def test_wrong_and_right_forms_become_a_mistake(self):
        self.analysis.analysis = {
            **VALID_ANALYSIS,
            "pitfall_wrong": "em cima do muro",
            "pitfall_right": "em cima do muro",
            "source_pitfall_wrong": "on the wall",
            "source_pitfall_right": "on the fence",
            "literal": "na cerca",
        }
        term = make_term(self.user, "on the fence")

        card = self.client.get(self.url(term)).json()["card"]

        self.assertEqual(card["mistake"], {"wrong": "on the wall", "right": "on the fence"})
        self.assertEqual(card["base"]["literal"], "na cerca")

    def test_card_saved_before_the_new_fields_still_opens(self):
        term = make_term(self.user, "gap")
        old = {
            key: value
            for key, value in VALID_ANALYSIS.items()
            if key
            not in {
                "pitfall_wrong",
                "pitfall_right",
                "literal",
                "imagine",
                "source_pitfall",
                "source_pitfall_wrong",
                "source_pitfall_right",
                "source_imagine",
                "source_formality_note",
                "source_contexts",
                "formality_note",
                "contexts",
                "dialogue",
            }
        }
        TermCard.objects.create(term=term, analysis=old, prompt_version="2.1", model="m")

        card = self.client.get(self.url(term)).json()["card"]

        self.assertEqual(self.analysis.calls, [])
        self.assertIsNone(card["base"]["literal"])
        self.assertIsNone(card["learning"]["pitfall"])
        self.assertIsNone(card["mistake"])
        self.assertEqual(card["dialogue"], [])
        self.assertIsNone(card["formality_note"])
        self.assertEqual(card["fits"], [])
        self.assertIsNone(card["base"]["formality_note"])
        self.assertEqual(card["base"]["fits"], [])

    def test_next_opens_read_the_saved_card(self):
        term = make_term(self.user, "on the fence")

        self.client.get(self.url(term))
        response = self.client.get(self.url(term))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(self.analysis.calls), 1)

    def test_without_capture_the_term_is_the_context(self):
        term = make_term(self.user, "on the fence")

        response = self.client.get(self.url(term))

        self.assertEqual(self.analysis.calls[0]["text"], "on the fence")
        self.assertEqual(response.json()["captures"], [])

    def test_uses_the_languages_of_the_term_course(self):
        spanish = make_course(self.user, "es", "en")
        term = make_term(self.user, "hola", course=spanish)

        self.client.get(self.url(term))

        call = self.analysis.calls[0]
        self.assertEqual((call["source_language"], call["target_language"]), ("es", "en"))

    def test_lists_where_the_term_was_seen_newest_first(self):
        term = make_term(self.user, "on the fence")
        older = self.analyzed("Still on the fence? Try it free.", days_ago=3)
        newer = self.analyzed("Most of the team is still ON THE FENCE.", days_ago=1)
        self.mark(older, "on the fence")
        self.mark(newer, "ON THE FENCE")
        ready = make_capture(self.user, text=TEXT, original_text=TEXT)
        self.mark(ready, "on the fence")
        discarded = self.analyzed(discarded_at=timezone.now())
        self.mark(discarded, "on the fence")
        elsewhere = self.analyzed(course=make_course(self.user, "en", "es"))
        self.mark(elsewhere, "on the fence")

        response = self.client.get(self.url(term))

        captures = response.json()["captures"]
        self.assertEqual([c["id"] for c in captures], [str(newer.id), str(older.id)])
        self.assertEqual(self.analysis.calls[0]["text"], newer.text)
        self.assertEqual(captures[0]["source"], "text")

    @override_settings(TERM_CARD_MAX_CAPTURES=1)
    def test_limits_the_captures(self):
        term = make_term(self.user, "gap")
        for days_ago in (1, 2):
            self.mark(self.analyzed("mind the gap", days_ago=days_ago), "gap")

        response = self.client.get(self.url(term))

        self.assertEqual(len(response.json()["captures"]), 1)

    def test_term_of_another_user_or_deleted_returns_404(self):
        theirs = make_term(make_user("bia@example.com"), "gap")
        deleted = make_term(self.user, "mind", deleted_at=timezone.now())

        for term in (theirs, deleted):
            with self.subTest(term=term.text):
                self.assertEqual(self.client.get(self.url(term)).status_code, 404)
        self.assertEqual(self.analysis.calls, [])

    def test_analysis_failure_saves_nothing(self):
        self.analysis.error = GeminiUnavailableError()
        term = make_term(self.user, "gap")

        response = self.client.get(self.url(term))

        self.assertEqual(response.status_code, 503)
        self.assertFalse(TermCard.objects.exists())
        self.assertEqual(Term.objects.get().translation, "")

    def test_requires_login(self):
        term = make_term(self.user, "gap")
        self.client.force_authenticate(None)

        self.assertEqual(self.client.get(self.url(term)).status_code, 401)


class RevealTermTests(TermCardApiTestCase):
    def reveal(self, term, **data):
        return self.client.patch(self.url(term), data, format="json")

    def test_revealed_card_stays_revealed(self):
        term = make_term(self.user, "gap")
        self.client.get(self.url(term))

        response = self.reveal(term, revealed=True)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["revealed"])
        self.assertTrue(self.client.get(self.url(term)).json()["revealed"])

    def test_cover_again(self):
        term = make_term(self.user, "gap")
        self.client.get(self.url(term))
        self.reveal(term, revealed=True)

        response = self.reveal(term, revealed=False)

        self.assertFalse(response.json()["revealed"])
        self.assertFalse(TermCard.objects.get().revealed)

    def test_pitfall_is_revealed_on_its_own(self):
        term = make_term(self.user, "gap")
        self.assertFalse(self.client.get(self.url(term)).json()["pitfall_revealed"])

        response = self.reveal(term, pitfall_revealed=True)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["pitfall_revealed"])
        self.assertFalse(response.json()["revealed"])
        card = TermCard.objects.get()
        self.assertTrue(card.pitfall_revealed)
        self.assertFalse(card.revealed)

    def test_formality_note_is_revealed_on_its_own(self):
        term = make_term(self.user, "gap")
        self.assertFalse(self.client.get(self.url(term)).json()["formality_revealed"])

        response = self.reveal(term, formality_revealed=True)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["formality_revealed"])
        self.assertFalse(response.json()["revealed"])
        self.assertFalse(response.json()["pitfall_revealed"])
        card = TermCard.objects.get()
        self.assertTrue(card.formality_revealed)
        self.assertFalse(card.pitfall_revealed)

        self.reveal(term, formality_revealed=False)

        self.assertFalse(TermCard.objects.get().formality_revealed)

    def test_empty_body_returns_400(self):
        term = make_term(self.user, "gap")
        self.client.get(self.url(term))

        response = self.reveal(term)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(set(response.json()), {"revealed"})

    def test_without_card_returns_404_and_builds_nothing(self):
        term = make_term(self.user, "gap")

        response = self.reveal(term, revealed=True)

        self.assertEqual(response.status_code, 404)
        self.assertEqual(self.analysis.calls, [])

    def test_invalid_body_returns_400(self):
        term = make_term(self.user, "gap")
        self.client.get(self.url(term))

        response = self.reveal(term, revealed="talvez", level=5)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(set(response.json()), {"revealed", "level"})
