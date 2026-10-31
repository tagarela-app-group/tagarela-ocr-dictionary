from django.conf import settings
from django.db import models

from apps.courses.models import Course


class Capture(models.Model):
    class Source(models.TextChoices):
        TEXT = "text", "Texto"
        AUDIO = "audio", "Áudio"
        PHOTO = "photo", "Foto"

    class Status(models.TextChoices):
        READY = "ready", "Pronta"
        ANALYZED = "analyzed", "Analisada"

    id = models.UUIDField(primary_key=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="captures"
    )
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="captures")
    source = models.CharField(max_length=10, choices=Source.choices)
    status = models.CharField(max_length=20, choices=Status.choices)
    text = models.TextField(blank=True)
    captured_at = models.DateTimeField()
    analyzed_at = models.DateTimeField(null=True, blank=True)
    discarded_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["user", "updated_at"], name="capture_user_updated_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.get_source_display()} {self.id}"


class CaptureTerm(models.Model):
    capture = models.ForeignKey(Capture, on_delete=models.CASCADE, related_name="terms")
    text = models.CharField(max_length=255)
    start = models.PositiveIntegerField()
    end = models.PositiveIntegerField()

    class Meta:
        ordering = ["start", "-end"]
        constraints = [
            models.UniqueConstraint(
                fields=["capture", "start", "end"], name="unique_capture_term_span"
            ),
        ]

    def __str__(self) -> str:
        return self.text
