from django.contrib import admin

from apps.exercises.models import Exercise


@admin.register(Exercise)
class ExerciseAdmin(admin.ModelAdmin):
    list_display = ("term", "kind", "variant", "served_count", "prompt_version", "created_at")
    list_filter = ("kind", "prompt_version")
    search_fields = ("term__text", "term__user__email")
    readonly_fields = (
        "term",
        "kind",
        "variant",
        "payload",
        "prompt_version",
        "model",
        "created_at",
    )
