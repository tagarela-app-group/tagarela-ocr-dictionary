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

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    term = models.ForeignKey(Term, on_delete=models.CASCADE, related_name="review_attempts")
    exercise = models.ForeignKey(
        Exercise, null=True, blank=True, on_delete=models.SET_NULL, related_name="attempts"
    )
    kind = models.CharField(max_length=30, choices=Exercise.Kind.choices)
    outcome = models.CharField(max_length=10, choices=Outcome.choices)
    level = models.PositiveSmallIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.term.text} · {self.outcome}"
