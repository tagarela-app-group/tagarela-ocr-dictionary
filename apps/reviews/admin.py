from django.contrib import admin

from apps.reviews.models import ReviewAttempt


@admin.register(ReviewAttempt)
class ReviewAttemptAdmin(admin.ModelAdmin):
    list_display = ("term", "kind", "outcome", "role", "points", "level", "played_at")
    list_filter = ("kind", "outcome", "role")
    search_fields = ("term__text", "term__user__email")
    readonly_fields = ("term", "exercise", "kind", "outcome", "level", "created_at")
