from django.db import models

from apps.vocabulary.models import Term


class TermCard(models.Model):
    term = models.OneToOneField(
        Term, on_delete=models.CASCADE, primary_key=True, related_name="card"
    )
    analysis = models.JSONField()
    prompt_version = models.CharField(max_length=20)
    model = models.CharField(max_length=100)
    revealed = models.BooleanField(default=False)
    pitfall_revealed = models.BooleanField(default=False)
    formality_revealed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.term.text
