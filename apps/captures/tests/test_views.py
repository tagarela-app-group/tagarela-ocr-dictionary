import uuid
from datetime import timedelta
from unittest.mock import patch

from django.utils import timezone
from rest_framework.test import APITestCase

from apps.captures.models import Capture, CaptureTerm
from apps.captures.tests.helpers import TEXT, UploadDirMixin, make_capture, make_user
from apps.captures.views import CapturePagination
from apps.ocr.tests.images import uploaded_image
from apps.transcription.tests.audio import uploaded_audio

URL = "/api/v1/captures"
CAPTURED_AT = "2026-10-23T10:00:00-03:00"
MIND_THE_GAP = {"text": "mind the gap", "start": 7, "end": 19}
MIND = {"text": "mind", "start": 7, "end": 11}
TRAIN = {"text": "train", "start": 32, "end": 37}


class CaptureApiTestCase(UploadDirMixin, APITestCase):
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
    def test_text_capture_is_born_ready(self):
        response = self.create()

        self.assertEqual(response.status_code, 201)
        body = response.json()
        self.assertEqual(body["status"], "ready")
        self.assertEqual(body["text"], TEXT)
        self.assertEqual(body["original_text"], TEXT)
        self.assertEqual(body["terms"], [])
        self.assertIsNotNone(body["processed_at"])
        self.assertEqual(Capture.objects.get().user, self.user)

    def test_photo_capture_waits_for_the_file(self):
        payload = {"id": str(uuid.uuid4()), "source": "photo", "captured_at": CAPTURED_AT}
        response = self.client.post(URL, payload, format="json")

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["status"], "waiting_file")
        self.assertEqual(response.json()["text"], "")

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

    def test_text_capture_without_text_returns_400(self):
        payload = {"id": str(uuid.uuid4()), "source": "text", "captured_at": CAPTURED_AT}

        response = self.client.post(URL, payload, format="json")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {"text": ["Escreva o texto da captura."]})

    def test_photo_with_text_returns_400(self):
        response = self.create(source="photo")

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

    def test_patch_when_not_ready_returns_409(self):
        capture = make_capture(self.user, status=Capture.Status.PROCESSING)

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


@patch("apps.captures.services.enqueue_processing")
class FileCaptureTests(CaptureApiTestCase):
    def put_file(self, capture: Capture, file=None):
        return self.client.put(
            self.url(capture, "/file"), {"file": file or uploaded_image()}, format="multipart"
        )

    def test_photo_file_is_saved_and_queued(self, enqueue):
        capture = make_capture(
            self.user, source=Capture.Source.PHOTO, status=Capture.Status.WAITING_FILE, text=""
        )

        with self.captureOnCommitCallbacks(execute=True):
            response = self.put_file(capture)

        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.json()["status"], "processing")
        self.assertEqual([path.name for path in self.upload_dir.iterdir()], [f"{capture.id}.png"])
        enqueue.assert_called_once_with(capture.id)

    def test_audio_file_is_saved_and_queued(self, enqueue):
        capture = make_capture(
            self.user, source=Capture.Source.AUDIO, status=Capture.Status.WAITING_FILE, text=""
        )

        with self.captureOnCommitCallbacks(execute=True):
            response = self.put_file(capture, uploaded_audio())

        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.json()["status"], "processing")
        self.assertEqual([path.name for path in self.upload_dir.iterdir()], [f"{capture.id}.m4a"])
        enqueue.assert_called_once_with(capture.id)

    def test_failed_photo_can_be_sent_again(self, enqueue):
        capture = make_capture(
            self.user,
            source=Capture.Source.PHOTO,
            status=Capture.Status.FAILED,
            error=Capture.Error.PROCESSING_FAILED,
            text="",
        )

        response = self.put_file(capture)

        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.json()["status"], "processing")
        self.assertEqual(response.json()["error"], "")

    def test_processed_capture_returns_409(self, enqueue):
        capture = make_capture(self.user, source=Capture.Source.PHOTO)

        response = self.put_file(capture)

        self.assertEqual(response.status_code, 409)
        enqueue.assert_not_called()

    def test_wrong_files_return_400(self, enqueue):
        cases = [
            (Capture.Source.TEXT, uploaded_image(), "Captura de texto não recebe arquivo."),
            (
                Capture.Source.AUDIO,
                uploaded_image(),
                "Formato inválido. Envie um áudio M4A (AAC).",
            ),
            (
                Capture.Source.PHOTO,
                uploaded_audio(),
                "Formato inválido. Envie uma imagem JPEG, PNG ou WEBP.",
            ),
            (
                Capture.Source.PHOTO,
                uploaded_image("GIF", "image/gif", "foto.gif"),
                "Formato inválido. Envie uma imagem JPEG, PNG ou WEBP.",
            ),
        ]

        for source, file, message in cases:
            with self.subTest(source=source):
                capture = make_capture(self.user, source=source, status="waiting_file", text="")
                response = self.put_file(capture, file)
                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.json(), {"file": [message]})

        enqueue.assert_not_called()


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

    def test_without_terms_returns_400(self):
        capture = make_capture(self.user)

        response = self.client.post(self.url(capture, "/confirm"))

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {"terms": ["Escolha pelo menos um termo."]})

    def test_not_ready_returns_409(self):
        capture = make_capture(self.user, status=Capture.Status.PROCESSING)

        response = self.client.post(self.url(capture, "/confirm"))

        self.assertEqual(response.status_code, 409)
