import uuid

from django.db import models

from apps.courses.models import Course
from apps.vocabulary.models import Term


class DailyWord(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="daily_words")
    date = models.DateField()
    text = models.CharField(max_length=255)
    kind = models.CharField(max_length=20, choices=Term.Kind.choices)
    phonetic = models.CharField(max_length=255, null=True, blank=True)
    example = models.TextField()
    meaning = models.TextField()
    prompt_version = models.CharField(max_length=20)
    model = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date"]
        constraints = [
            models.UniqueConstraint(fields=["course", "date"], name="unique_daily_word_per_day"),
        ]

    def __str__(self) -> str:
        return self.text
