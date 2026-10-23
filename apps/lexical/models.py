from django.db import models


class LexicalEntry(models.Model):
    word = models.CharField(max_length=255)
    normalized_word = models.CharField(max_length=255)
    language = models.CharField(max_length=10)
    data = models.JSONField()
    source = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["normalized_word", "language"],
                name="unique_lexical_entry",
            )
        ]
        indexes = [
            models.Index(
                fields=["language", "normalized_word"],
                name="lexical_ent_languag_f32419_idx",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.normalized_word} ({self.language})"
