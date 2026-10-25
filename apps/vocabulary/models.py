import uuid

from django.conf import settings
from django.db import models
from django.db.models.functions import Lower


class Group(models.Model):
    class Accent(models.TextChoices):
        VIOLET = "violet", "Violeta"
        CORAL = "coral", "Coral"
        MINT = "mint", "Menta"
        MANGO = "mango", "Manga"
        SKY = "sky", "Céu"
        PINK = "pink", "Rosa"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="term_groups"
    )
    name = models.CharField(max_length=100)
    icon = models.CharField(max_length=30)
    accent = models.CharField(max_length=10, choices=Accent.choices)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(Lower("name"), "user", name="unique_group_name_per_user"),
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
    group = models.ForeignKey(
        Group, null=True, blank=True, on_delete=models.SET_NULL, related_name="terms"
    )
    text = models.CharField(max_length=255)
    key = models.CharField(max_length=255)
    kind = models.CharField(max_length=20, choices=Kind.choices)
    translation = models.CharField(max_length=255, blank=True)
    level = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["user", "key"], name="unique_term_per_user"),
        ]

    def __str__(self) -> str:
        return self.text
