import uuid

from django.conf import settings
from django.db import models
from django.db.models import F, Q


class Course(models.Model):
    class Language(models.TextChoices):
        EN = "en", "Inglês"
        ES = "es", "Espanhol"
        PT = "pt", "Português"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="courses"
    )
    learning = models.CharField(max_length=2, choices=Language.choices)
    base = models.CharField(max_length=2, choices=Language.choices)
    active = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "learning", "base"], name="unique_course_per_user"
            ),
            models.UniqueConstraint(
                fields=["user"], condition=Q(active=True), name="one_active_course_per_user"
            ),
            models.CheckConstraint(
                condition=~Q(learning=F("base")), name="course_learns_another_language"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.get_learning_display()} por meio do {self.get_base_display()}"
