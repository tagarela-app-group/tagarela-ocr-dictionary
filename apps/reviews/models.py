import uuid

from django.db import models

from apps.exercises.models import Exercise
from apps.vocabulary.models import Term


class ReviewAttempt(models.Model):
    class Outcome(models.TextChoices):
        FIRST = "first", "De primeira"
        RETRY = "retry", "Depois de errar"
        HINT = "hint", "Com dica"
        MISSED = "missed", "Viu a resposta"

    class Role(models.TextChoices):
        FIRST_REVIEW = "first_review", "Primeira revisão"
        SESSION = "session", "Sessão"
        RETEST = "retest", "Reteste"
        EXTRA = "extra", "Sem efeito"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    term = models.ForeignKey(Term, on_delete=models.CASCADE, related_name="review_attempts")
    exercise = models.ForeignKey(
        Exercise, null=True, blank=True, on_delete=models.SET_NULL, related_name="attempts"
    )
    kind = models.CharField(max_length=30, choices=Exercise.Kind.choices)
    outcome = models.CharField(max_length=10, choices=Outcome.choices)
    role = models.CharField(max_length=12, choices=Role.choices)
    played_at = models.DateTimeField()
    local_date = models.DateField()
    seen_sentence = models.BooleanField(default=False)
    used_slow = models.BooleanField(default=False)
    errors = models.PositiveSmallIntegerField(default=0)
    hints = models.PositiveSmallIntegerField(default=0)
    audio_replays = models.PositiveSmallIntegerField(default=0)
    response_ms = models.PositiveIntegerField(null=True, blank=True)
    points = models.FloatField(default=0.0)
    level_before = models.PositiveSmallIntegerField()
    level = models.PositiveSmallIntegerField()
    interval_before = models.FloatField()
    interval_days = models.FloatField()
    due_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.term.text} · {self.outcome}"
