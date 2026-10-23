from django.test import TestCase

from apps.captures.models import Capture
from apps.captures.processing import CaptureProcessingError, CaptureProcessingService
from apps.captures.tests.helpers import UploadDirMixin, make_capture, make_user


class FakeExtractor:
    def __init__(self, text: str = "", error: Exception | None = None) -> None:
        self.text = text
        self.error = error
        self.paths = []

    def __call__(self, path):
        self.paths.append(path)
        if self.error:
            raise self.error

        return self.text


class CaptureProcessingServiceTests(UploadDirMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.capture = make_capture(
            make_user(),
            source=Capture.Source.PHOTO,
            status=Capture.Status.PROCESSING,
            original_text="",
            text="",
        )
        self.file = self.upload_dir / f"{self.capture.id}.png"
        self.file.write_bytes(b"image")

    def process(self, extractor: FakeExtractor, final_attempt: bool = False) -> Capture:
        service = CaptureProcessingService({Capture.Source.PHOTO: extractor})
        service.process(self.capture.id, final_attempt=final_attempt)
        self.capture.refresh_from_db()

        return self.capture

    def test_extracted_text_makes_capture_ready_and_deletes_file(self):
        extractor = FakeExtractor("  MIND THE GAP ")

        capture = self.process(extractor)

        self.assertEqual(capture.status, Capture.Status.READY)
        self.assertEqual((capture.text, capture.original_text), ("MIND THE GAP", "MIND THE GAP"))
        self.assertIsNotNone(capture.processed_at)
        self.assertEqual(extractor.paths, [self.file])
        self.assertFalse(self.file.exists())

    def test_no_text_fails_with_no_text(self):
        capture = self.process(FakeExtractor("   "))

        self.assertEqual((capture.status, capture.error), ("failed", "no_text"))
        self.assertFalse(self.file.exists())

    def test_error_before_last_attempt_keeps_file_for_retry(self):
        with self.assertRaises(CaptureProcessingError):
            self.process(FakeExtractor(error=RuntimeError("paddle")))

        self.capture.refresh_from_db()
        self.assertEqual(self.capture.status, Capture.Status.PROCESSING)
        self.assertTrue(self.file.exists())

    def test_error_on_last_attempt_fails_and_deletes_file(self):
        capture = self.process(FakeExtractor(error=RuntimeError("paddle")), final_attempt=True)

        self.assertEqual((capture.status, capture.error), ("failed", "processing_failed"))
        self.assertFalse(self.file.exists())

    def test_missing_file_fails(self):
        self.file.unlink()

        capture = self.process(FakeExtractor("text"))

        self.assertEqual((capture.status, capture.error), ("failed", "file_missing"))

    def test_capture_not_processing_is_left_alone(self):
        Capture.objects.filter(pk=self.capture.pk).update(status=Capture.Status.READY)
        extractor = FakeExtractor("text")

        capture = self.process(extractor)

        self.assertEqual(capture.status, Capture.Status.READY)
        self.assertEqual(extractor.paths, [])

    def test_photo_and_audio_have_default_extractors(self):
        self.assertEqual(
            set(CaptureProcessingService().extractors),
            {Capture.Source.PHOTO, Capture.Source.AUDIO},
        )
