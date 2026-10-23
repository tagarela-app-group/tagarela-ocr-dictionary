import tempfile
import uuid
from pathlib import Path

from django.contrib.auth import get_user_model
from django.test import override_settings
from django.utils import timezone

from apps.captures.models import Capture

TEXT = "Please mind the gap between the train and the platform."


class UploadDirMixin:
    def setUp(self):
        super().setUp()
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.upload_dir = Path(temp.name)
        override = override_settings(CAPTURE_UPLOAD_DIR=self.upload_dir)
        override.enable()
        self.addCleanup(override.disable)


def make_user(email: str = "ana@example.com"):
    return get_user_model().objects.create_user(email, "s3nha-forte-123", name="Ana")


def make_capture(user, **fields) -> Capture:
    defaults = {
        "id": uuid.uuid4(),
        "user": user,
        "source": Capture.Source.TEXT,
        "status": Capture.Status.READY,
        "original_text": TEXT,
        "text": TEXT,
        "captured_at": timezone.now(),
    }
    return Capture.objects.create(**{**defaults, **fields})
