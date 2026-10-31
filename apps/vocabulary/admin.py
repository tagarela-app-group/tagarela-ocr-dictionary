from django.contrib import admin

from apps.vocabulary.models import Group, Term


@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    list_display = ("name", "course", "icon", "accent", "created_at")
    list_filter = ("accent",)
    search_fields = ("name", "course__user__email")
    readonly_fields = ("id", "created_at")


@admin.register(Term)
class TermAdmin(admin.ModelAdmin):
    list_display = ("text", "user", "group", "kind", "level", "created_at")
    list_filter = ("kind", "level")
    search_fields = ("text", "user__email")
    readonly_fields = ("id", "user", "key", "created_at")
