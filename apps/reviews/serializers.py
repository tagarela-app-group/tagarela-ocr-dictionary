import uuid

from rest_framework import serializers

from apps.common.serializers import StrictSerializer
from apps.exercises.models import Exercise
from apps.reviews.models import ReviewAttempt
from apps.vocabulary.serializers import TermSerializer


class AttemptSerializer(StrictSerializer):
    id = serializers.UUIDField(default=uuid.uuid4)
    term = serializers.UUIDField()
    kind = serializers.ChoiceField(choices=Exercise.Kind.choices)
    exercise = serializers.UUIDField(required=False, allow_null=True)
    outcome = serializers.ChoiceField(choices=ReviewAttempt.Outcome.choices)


class RoundSerializer(serializers.Serializer):
    term = TermSerializer()
    kind = serializers.CharField()


class SessionSerializer(serializers.Serializer):
    due = serializers.IntegerField()
    rounds = RoundSerializer(many=True)
