from celery import shared_task
from django.conf import settings

from apps.captures.processing import CaptureProcessingError, CaptureProcessingService


@shared_task(bind=True, max_retries=None)
def process_capture(self, capture_id: str) -> None:
    retries = self.request.retries
    final_attempt = retries >= settings.CAPTURE_PROCESS_MAX_RETRIES

    try:
        CaptureProcessingService().process(capture_id, final_attempt=final_attempt)
    except CaptureProcessingError as exc:
        raise self.retry(exc=exc, countdown=settings.CAPTURE_PROCESS_RETRY_SECONDS * 2**retries)


def enqueue_processing(capture_id) -> None:
    process_capture.delay(str(capture_id))
