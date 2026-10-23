from django.contrib import admin

from apps.captures.models import Capture, CaptureTerm


class CaptureTermInline(admin.TabularInline):
    model = CaptureTerm
    extra = 0
    fields = ("text", "start", "end")
    readonly_fields = fields
    can_delete = False


@admin.register(Capture)
class CaptureAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "source", "status", "captured_at", "updated_at")
    list_filter = ("source", "status")
    search_fields = ("text", "user__email")
    readonly_fields = ("id", "user", "source", "captured_at", "created_at", "updated_at")
    inlines = [CaptureTermInline]
