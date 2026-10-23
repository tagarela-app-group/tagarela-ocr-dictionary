from django.utils import timezone

from apps.captures.models import Capture
from apps.captures.uploads import delete_upload, find_upload
from apps.ocr.services import TextExtractionService


class CaptureProcessingError(Exception):
    pass


class CaptureProcessingService:
    def __init__(self, extractors: dict | None = None) -> None:
        self.extractors = extractors or {
            Capture.Source.PHOTO: TextExtractionService().extract,
        }

    def process(self, capture_id, final_attempt: bool) -> None:
        capture = Capture.objects.filter(pk=capture_id, status=Capture.Status.PROCESSING).first()
        if capture is None:
            return

        path = find_upload(capture.id)
        if path is None:
            self._fail(capture, Capture.Error.FILE_MISSING)
            return

        try:
            text = self.extractors[capture.source](path).strip()
        except Exception as exc:
            if not final_attempt:
                raise CaptureProcessingError(str(exc)) from exc
            delete_upload(capture.id)
            self._fail(capture, Capture.Error.PROCESSING_FAILED)
            return

        delete_upload(capture.id)
        if not text:
            self._fail(capture, Capture.Error.NO_TEXT)
            return

        capture.original_text = text
        capture.text = text
        capture.status = Capture.Status.READY
        capture.error = ""
        capture.processed_at = timezone.now()
        capture.save()

    def _fail(self, capture: Capture, error: str) -> None:
        capture.status = Capture.Status.FAILED
        capture.error = error
        capture.save(update_fields=["status", "error", "updated_at"])
