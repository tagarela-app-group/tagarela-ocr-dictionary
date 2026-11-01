import uuid
from datetime import UTC, timedelta
from datetime import date as Date

from django.conf import settings
from django.utils import timezone
from rest_framework import serializers

from apps.common.serializers import StrictSerializer
from apps.exercises.models import Exercise
from apps.reviews import policy
from apps.reviews.models import ReviewAttempt
from apps.vocabulary.serializers import TermSerializer

FAR_DATE = "A data do aparelho está muito longe da data certa."
MAX_OFFSET_MINUTES = 14 * 60


def too_far(given: Date, reference: Date) -> bool:
    return abs((given - reference).days) > settings.REVIEW_DATE_TOLERANCE_DAYS


class SessionQuerySerializer(StrictSerializer):
    kinds = serializers.ListField(child=serializers.CharField(allow_blank=True), required=False)
    date = serializers.DateField(required=False)
    offset = serializers.IntegerField(
        default=0, min_value=-MAX_OFFSET_MINUTES, max_value=MAX_OFFSET_MINUTES
    )

    def validate_date(self, value: Date) -> Date:
        if too_far(value, timezone.now().astimezone(UTC).date()):
            raise serializers.ValidationError(FAR_DATE)

        return value


class AttemptSerializer(StrictSerializer):
    id = serializers.UUIDField(default=uuid.uuid4)
    term = serializers.UUIDField()
    kind = serializers.ChoiceField(choices=Exercise.Kind.choices)
    exercise = serializers.UUIDField(required=False, allow_null=True)
    outcome = serializers.ChoiceField(choices=ReviewAttempt.Outcome.choices)
    played_at = serializers.DateTimeField(required=False)
    local_date = serializers.DateField(required=False)
    used_slow = serializers.BooleanField(default=False)
    errors = serializers.IntegerField(default=0, min_value=0, max_value=1000)
    hints = serializers.IntegerField(default=0, min_value=0, max_value=1000)
    audio_replays = serializers.IntegerField(default=0, min_value=0, max_value=1000)
    response_ms = serializers.IntegerField(required=False, allow_null=True, min_value=0)

    def validate(self, attrs):
        played_at = attrs.get("played_at")
        tolerance = timedelta(days=settings.REVIEW_DATE_TOLERANCE_DAYS)
        if played_at is not None and played_at > timezone.now() + tolerance:
            raise serializers.ValidationError({"played_at": [FAR_DATE]})

        local_date = attrs.get("local_date")
        reference = played_at or timezone.now()
        if local_date is not None and too_far(local_date, reference.astimezone(UTC).date()):
            raise serializers.ValidationError({"local_date": [FAR_DATE]})

        return attrs


class StudySerializer(StrictSerializer):
    event = serializers.ChoiceField(choices=("read", "listened"))


class EffectSerializer(serializers.ModelSerializer):
    rating = serializers.SerializerMethodField()

    class Meta:
        model = ReviewAttempt
        fields = (
            "role",
            "points",
            "rating",
            "level_before",
            "level",
            "interval_before",
            "interval_days",
            "due_at",
        )

    def get_rating(self, attempt: ReviewAttempt) -> str:
        return policy.rating(attempt.points)


class RoundSerializer(serializers.Serializer):
    term = TermSerializer()
    kind = serializers.CharField()
    retest = serializers.BooleanField()


class SessionSerializer(serializers.Serializer):
    due = serializers.IntegerField()
    limit = serializers.IntegerField()
    done = serializers.IntegerField()
    waiting = serializers.IntegerField()
    unread = serializers.IntegerField()
    next_due_at = serializers.DateTimeField(allow_null=True)
    rounds = RoundSerializer(many=True)
