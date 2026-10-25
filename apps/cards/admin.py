from django.contrib import admin

from apps.cards.models import TermCard


@admin.register(TermCard)
class TermCardAdmin(admin.ModelAdmin):
    list_display = ("term", "prompt_version", "model", "revealed", "created_at")
    list_filter = ("prompt_version", "revealed")
    search_fields = ("term__text", "term__user__email")
    readonly_fields = ("term", "analysis", "prompt_version", "model", "created_at", "updated_at")
