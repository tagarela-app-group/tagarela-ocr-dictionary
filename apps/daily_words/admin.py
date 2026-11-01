from django.contrib import admin

from apps.daily_words.models import DailyWord


@admin.register(DailyWord)
class DailyWordAdmin(admin.ModelAdmin):
    list_display = ("text", "course", "date")
    search_fields = ("text", "course__user__email")
    readonly_fields = ("prompt_version", "model", "created_at")
