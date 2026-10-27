import uuid

from django.db import models

from apps.vocabulary.models import Term


class Exercise(models.Model):
    class Kind(models.TextChoices):
        LISTEN_WRITE = "listen_write", "Ouvir e escrever"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    term = models.ForeignKey(Term, on_delete=models.CASCADE, related_name="exercises")
    kind = models.CharField(max_length=30, choices=Kind.choices)
    variant = models.PositiveSmallIntegerField()
    payload = models.JSONField()
    prompt_version = models.CharField(max_length=20)
    model = models.CharField(max_length=100)
    served_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["served_count", "variant"]
        constraints = [
            models.UniqueConstraint(
                fields=["term", "kind", "variant"], name="unique_exercise_variant"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.term.text} · {self.kind} {self.variant}"
