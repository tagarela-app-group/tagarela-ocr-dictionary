import uuid
from bisect import bisect_right

from django.conf import settings
from django.db import models
from django.db.models.functions import Lower

from apps.courses.models import Course


def start_interval_days() -> float:
    return settings.REVIEW_START_INTERVAL_DAYS


def first_review_days() -> float:
    return settings.REVIEW_FIRST_REVIEW_DAYS


class Group(models.Model):
    class Accent(models.TextChoices):
        VIOLET = "violet", "Violeta"
        CORAL = "coral", "Coral"
        MINT = "mint", "Menta"
        MANGO = "mango", "Manga"
        SKY = "sky", "Céu"
        PINK = "pink", "Rosa"
        GRAPE = "grape", "Uva"
        COCOA = "cocoa", "Cacau"
        LIME = "lime", "Lima"
        GOLD = "gold", "Ouro"
        TEAL = "teal", "Turquesa"
        SLATE = "slate", "Ardósia"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="groups")
    name = models.CharField(max_length=100)
    icon = models.CharField(max_length=30)
    accent = models.CharField(max_length=10, choices=Accent.choices)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(Lower("name"), "course", name="unique_group_name_per_course"),
        ]

    def __str__(self) -> str:
        return self.name


class Term(models.Model):
    class Kind(models.TextChoices):
        WORD = "word", "Palavra"
        EXPRESSION = "expression", "Expressão"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="terms"
    )
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="terms")
    group = models.ForeignKey(
        Group, null=True, blank=True, on_delete=models.SET_NULL, related_name="terms"
    )
    text = models.CharField(max_length=255)
    key = models.CharField(max_length=255)
    kind = models.CharField(max_length=20, choices=Kind.choices)
    translation = models.CharField(max_length=255, blank=True)
    interval_days = models.FloatField(default=start_interval_days)
    scheduled_days = models.FloatField(default=first_review_days)
    due_at = models.DateTimeField(null=True, blank=True)
    last_session_at = models.DateTimeField(null=True, blank=True)
    ease = models.FloatField(default=1.0)
    first_read_at = models.DateTimeField(null=True, blank=True)
    audio_heard_at = models.DateTimeField(null=True, blank=True)
    study_points = models.FloatField(default=0.0)
    created_at = models.DateTimeField(auto_now_add=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["course", "key"], name="unique_term_per_course"),
        ]

    def __str__(self) -> str:
        return self.text

    @property
    def level(self) -> int:
        return bisect_right(settings.REVIEW_LEVEL_DAYS, self.interval_days)
