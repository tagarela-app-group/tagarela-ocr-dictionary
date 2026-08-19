from django.contrib import admin

from apps.lexical.models import LexicalEntry


@admin.register(LexicalEntry)
class LexicalEntryAdmin(admin.ModelAdmin):
    list_display = ("normalized_word", "language", "source", "updated_at")
    search_fields = ("word", "normalized_word")
    list_filter = ("language", "source")
