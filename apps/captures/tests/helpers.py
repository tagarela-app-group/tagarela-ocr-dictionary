import uuid

from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.captures.models import Capture
from apps.courses.tests.helpers import make_course

TEXT = "Please mind the gap between the train and the platform."


def make_user(email: str = "ana@example.com"):
    return get_user_model().objects.create_user(email, "s3nha-forte-123", name="Ana")


def make_capture(user, **fields) -> Capture:
    fields.setdefault("course", make_course(user))
    defaults = {
        "id": uuid.uuid4(),
        "user": user,
        "source": Capture.Source.TEXT,
        "status": Capture.Status.READY,
        "text": TEXT,
        "captured_at": timezone.now(),
    }
    return Capture.objects.create(**{**defaults, **fields})
