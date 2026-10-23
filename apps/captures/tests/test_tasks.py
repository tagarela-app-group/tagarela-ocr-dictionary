import uuid
from unittest.mock import patch

from django.test import SimpleTestCase, override_settings

from apps.captures.processing import CaptureProcessingError
from apps.captures.tasks import enqueue_processing, process_capture


class RetryRequested(Exception):
    pass


@override_settings(CAPTURE_PROCESS_MAX_RETRIES=3, CAPTURE_PROCESS_RETRY_SECONDS=30)
@patch("apps.captures.tasks.CaptureProcessingService")
class ProcessCaptureTaskTests(SimpleTestCase):
    def test_first_attempt_is_not_final(self, service_class):
        process_capture.apply(args=["capture-id"])

        service_class.return_value.process.assert_called_once_with(
            "capture-id", final_attempt=False
        )

    def test_attempt_after_max_retries_is_final(self, service_class):
        process_capture.apply(args=["capture-id"], retries=3)

        service_class.return_value.process.assert_called_once_with("capture-id", final_attempt=True)

    def test_processing_error_retries_with_growing_wait(self, service_class):
        error = CaptureProcessingError("paddle")
        service_class.return_value.process.side_effect = error

        with (
            patch.object(process_capture, "retry", side_effect=RetryRequested) as retry,
            self.assertRaises(RetryRequested),
        ):
            process_capture.run("capture-id")

        retry.assert_called_once_with(exc=error, countdown=30)


class EnqueueProcessingTests(SimpleTestCase):
    def test_sends_capture_id_as_text(self):
        capture_id = uuid.uuid4()

        with patch.object(process_capture, "delay") as delay:
            enqueue_processing(capture_id)

        delay.assert_called_once_with(str(capture_id))
