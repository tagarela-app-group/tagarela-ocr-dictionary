from django.contrib import admin

from apps.courses.models import Course


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ("user", "learning", "base", "active", "created_at")
    list_filter = ("learning", "base", "active")
    search_fields = ("user__email",)
    readonly_fields = ("id", "user", "created_at")
