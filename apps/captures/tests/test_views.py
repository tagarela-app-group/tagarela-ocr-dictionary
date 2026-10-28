import uuid
from datetime import timedelta
from unittest.mock import patch

from django.utils import timezone
from rest_framework.test import APITestCase

from apps.captures.models import Capture, CaptureTerm
from apps.captures.tests.helpers import TEXT, make_capture, make_user
from apps.captures.views import CapturePagination
from apps.courses.models import Course
from apps.courses.tests.helpers import make_course
from apps.vocabulary.models import Term
from apps.vocabulary.tests.helpers import make_group, make_term

URL = "/api/v1/captures"
CAPTURED_AT = "2026-10-23T10:00:00-03:00"
MIND_THE_GAP = {"text": "mind the gap", "start": 7, "end": 19}
MIND = {"text": "mind", "start": 7, "end": 11}
TRAIN = {"text": "train", "start": 32, "end": 37}


class CaptureApiTestCase(APITestCase):
    def setUp(self):
        super().setUp()
        self.user = make_user()
        self.client.force_authenticate(self.user)

    def url(self, capture: Capture, suffix: str = "") -> str:
        return f"{URL}/{capture.id}{suffix}"

    def create(self, **data):
        payload = {
            "id": str(uuid.uuid4()),
            "source": "text",
            "captured_at": CAPTURED_AT,
            "text": TEXT,
            **data,
        }
        return self.client.post(URL, payload, format="json")


class CreateCaptureTests(CaptureApiTestCase):
    def test_any_source_with_text_from_the_app_is_born_ready(self):
        for source in ("text", "photo", "audio"):
            with self.subTest(source=source):
                response = self.create(source=source)

                self.assertEqual(response.status_code, 201)
                body = response.json()
                self.assertEqual(body["status"], "ready")
                self.assertEqual(body["text"], TEXT)
                self.assertEqual(body["original_text"], TEXT)
                self.assertEqual(body["terms"], [])
                self.assertIsNotNone(body["processed_at"])
                self.assertEqual(Capture.objects.get(id=body["id"]).user, self.user)

    def test_same_id_again_returns_the_existing_capture(self):
        capture_id = str(uuid.uuid4())
        self.create(id=capture_id)

        response = self.create(id=capture_id, text="Another text")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["text"], TEXT)
        self.assertEqual(Capture.objects.count(), 1)

    def test_id_of_another_user_returns_409(self):
        other = make_capture(make_user("bia@example.com"))

        response = self.create(id=str(other.id))

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json(), {"detail": "Esse id já está em uso."})

    def test_any_source_without_text_returns_400(self):
        for source in ("text", "photo", "audio"):
            with self.subTest(source=source):
                payload = {"id": str(uuid.uuid4()), "source": source, "captured_at": CAPTURED_AT}

                response = self.client.post(URL, payload, format="json")

                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.json(), {"text": ["Escreva o texto da captura."]})

        self.assertFalse(Capture.objects.exists())

    def test_photo_with_blank_text_returns_400(self):
        response = self.create(source="photo", text="")

        self.assertEqual(response.status_code, 400)
        self.assertIn("text", response.json())

    def test_unknown_field_returns_400(self):
        response = self.create(user=99, status="analyzed")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json(),
            {"status": ["Campo não permitido."], "user": ["Campo não permitido."]},
        )

    def test_invalid_values_return_400(self):
        response = self.create(id="abc", source="video", captured_at="ontem", text="x" * 2001)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(set(response.json()), {"id", "source", "captured_at", "text"})

    def test_without_login_returns_401(self):
        response = self.client_class().post(URL, {}, format="json")

        self.assertEqual(response.status_code, 401)


class ListCaptureTests(CaptureApiTestCase):
    def test_lists_own_captures_newest_first_without_discarded(self):
        older = make_capture(self.user)
        newer = make_capture(self.user)
        make_capture(self.user, discarded_at=timezone.now())
        make_capture(make_user("bia@example.com"))

        response = self.client.get(URL)

        self.assertEqual(response.status_code, 200)
        ids = [item["id"] for item in response.json()["results"]]
        self.assertEqual(ids, [str(newer.id), str(older.id)])
        self.assertIsNone(response.json()["next"])

    def test_updated_since_returns_changes_including_discarded(self):
        old = make_capture(self.user)
        Capture.objects.filter(pk=old.pk).update(updated_at=timezone.now() - timedelta(days=2))
        discarded = make_capture(self.user, discarded_at=timezone.now())
        since = (timezone.now() - timedelta(days=1)).isoformat()

        response = self.client.get(URL, {"updated_since": since})

        self.assertEqual(response.status_code, 200)
        results = response.json()["results"]
        self.assertEqual([item["id"] for item in results], [str(discarded.id)])
        self.assertIsNotNone(results[0]["discarded_at"])

    def test_paginates_with_cursor(self):
        for _ in range(3):
            make_capture(self.user)

        with patch.object(CapturePagination, "page_size", 2):
            first = self.client.get(URL).json()
            second = self.client.get(first["next"]).json()

        self.assertEqual(len(first["results"]), 2)
        self.assertEqual(len(second["results"]), 1)
        self.assertIsNone(second["next"])

    def test_invalid_query_returns_400(self):
        response = self.client.get(URL, {"updated_since": "ontem", "page": 2})

        self.assertEqual(response.status_code, 400)
        self.assertEqual(set(response.json()), {"updated_since", "page"})


class DetailCaptureTests(CaptureApiTestCase):
    def test_get_own_capture(self):
        capture = make_capture(self.user)

        response = self.client.get(self.url(capture))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["id"], str(capture.id))

    def test_capture_of_another_user_or_discarded_returns_404(self):
        other = make_capture(make_user("bia@example.com"))
        discarded = make_capture(self.user, discarded_at=timezone.now())

        self.assertEqual(self.client.get(self.url(other)).status_code, 404)
        self.assertEqual(self.client.get(self.url(discarded)).status_code, 404)
        self.assertEqual(self.client.patch(self.url(other), {}, format="json").status_code, 404)

    def test_patch_saves_terms_word_inside_expression_included(self):
        capture = make_capture(self.user)

        response = self.client.patch(
            self.url(capture), {"terms": [MIND, MIND_THE_GAP]}, format="json"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["terms"], [MIND_THE_GAP, MIND])

    def test_patch_text_keeps_terms_that_still_match(self):
        capture = make_capture(self.user)
        CaptureTerm.objects.create(capture=capture, **MIND_THE_GAP)
        CaptureTerm.objects.create(capture=capture, **TRAIN)
        new_text = TEXT.replace("train", "bus")

        response = self.client.patch(self.url(capture), {"text": new_text}, format="json")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["text"], new_text)
        self.assertEqual(response.json()["original_text"], TEXT)
        self.assertEqual(response.json()["terms"], [MIND_THE_GAP])

    def test_patch_text_and_terms_validates_against_new_text(self):
        capture = make_capture(self.user)
        new_text = "I'm on the fence about it."
        fence = {"text": "on the fence", "start": 4, "end": 16}

        response = self.client.patch(
            self.url(capture), {"text": new_text, "terms": [fence]}, format="json"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["terms"], [fence])

    def test_term_that_does_not_match_text_returns_400(self):
        capture = make_capture(self.user)
        wrong = {**MIND, "text": "gap"}

        response = self.client.patch(self.url(capture), {"terms": [wrong]}, format="json")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {"terms": ["O termo 1 não bate com o trecho do texto."]})

    def test_repeated_term_returns_400(self):
        capture = make_capture(self.user)

        response = self.client.patch(self.url(capture), {"terms": [MIND, MIND]}, format="json")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {"terms": ["O termo 2 está repetido."]})

    def test_invalid_patch_bodies_return_400(self):
        capture = make_capture(self.user)
        bodies = [
            {},
            {"status": "analyzed"},
            {"terms": [{**MIND, "start": 11, "end": 7}]},
            {"terms": [{**MIND, "extra": True}]},
            {"terms": [MIND] * 51},
        ]

        for body in bodies:
            with self.subTest(body=body):
                response = self.client.patch(self.url(capture), body, format="json")
                self.assertEqual(response.status_code, 400)

    def test_patch_when_analyzed_returns_409(self):
        capture = make_capture(self.user, status=Capture.Status.ANALYZED)

        response = self.client.patch(self.url(capture), {"terms": [MIND]}, format="json")

        self.assertEqual(response.status_code, 409)

    def test_delete_discards_and_keeps_the_record(self):
        capture = make_capture(self.user)

        first = self.client.delete(self.url(capture))
        second = self.client.delete(self.url(capture))

        self.assertEqual((first.status_code, second.status_code), (204, 204))
        self.assertEqual(self.client.get(self.url(capture)).status_code, 404)
        capture.refresh_from_db()
        self.assertIsNotNone(capture.discarded_at)

    def test_delete_capture_of_another_user_returns_404(self):
        other = make_capture(make_user("bia@example.com"))

        response = self.client.delete(self.url(other))

        self.assertEqual(response.status_code, 404)
        other.refresh_from_db()
        self.assertIsNone(other.discarded_at)


class ConfirmCaptureTests(CaptureApiTestCase):
    def test_ready_capture_with_terms_becomes_analyzed(self):
        capture = make_capture(self.user)
        CaptureTerm.objects.create(capture=capture, **MIND_THE_GAP)

        response = self.client.post(self.url(capture, "/confirm"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "analyzed")
        self.assertIsNotNone(response.json()["analyzed_at"])

        again = self.client.post(self.url(capture, "/confirm"))
        self.assertEqual(again.status_code, 200)

    def test_confirmed_terms_enter_the_vocabulary_without_repeating(self):
        travel = make_group(self.user)
        make_term(self.user, "Train", travel)
        capture = make_capture(self.user)
        for term in (MIND_THE_GAP, MIND, TRAIN):
            CaptureTerm.objects.create(capture=capture, **term)

        self.client.post(self.url(capture, "/confirm"))
        self.client.post(self.url(capture, "/confirm"))

        terms = {t.text: t.group for t in Term.objects.filter(user=self.user)}
        self.assertEqual(terms, {"mind the gap": None, "mind": None, "Train": travel})

    def test_without_terms_returns_400(self):
        capture = make_capture(self.user)

        response = self.client.post(self.url(capture, "/confirm"))

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {"terms": ["Escolha pelo menos um termo."]})
        self.assertFalse(Term.objects.exists())


class CaptureCourseTests(CaptureApiTestCase):
    def setUp(self):
        super().setUp()
        self.english = make_course(self.user)
        self.spanish = make_course(self.user, "es", "pt")

    def test_capture_without_course_enters_the_active_one(self):
        response = self.create()

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["course"], str(self.english.id))
        self.assertEqual(Capture.objects.get().course, self.english)

    def test_capture_keeps_the_course_it_was_made_in(self):
        response = self.create(course=str(self.spanish.id))

        self.assertEqual(response.json()["course"], str(self.spanish.id))
        self.assertEqual(Capture.objects.get().course, self.spanish)

    def test_course_of_another_user_returns_400(self):
        other = make_course(make_user("bia@example.com"))

        response = self.create(course=str(other.id))

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {"course": ["Esse curso não existe."]})
        self.assertFalse(Capture.objects.exists())

    def test_list_brings_every_course(self):
        make_capture(self.user, course=self.english)
        make_capture(self.user, course=self.spanish)

        results = self.client.get(URL).json()["results"]

        courses = {item["course"] for item in results}
        self.assertEqual(courses, {str(self.english.id), str(self.spanish.id)})

    def test_confirm_sends_terms_to_the_capture_course(self):
        capture = make_capture(self.user, course=self.spanish)
        CaptureTerm.objects.create(capture=capture, **MIND)
        make_term(self.user, "mind", course=self.english)

        self.client.post(self.url(capture, "/confirm"))

        self.assertEqual(Term.objects.get(course=self.spanish).text, "mind")
        self.assertEqual(Term.objects.filter(course=self.english).count(), 1)
        self.assertEqual(Course.objects.get(active=True), self.english)
