import random

from django.conf import settings
from django.db import transaction
from django.db.models import F
from django.http import Http404
from rest_framework import serializers, status
from rest_framework.exceptions import APIException

from apps.courses.models import Course
from apps.exercises.models import Exercise
from apps.reviews.models import ReviewAttempt
from apps.reviews.policy import StepPolicy
from apps.vocabulary.models import Term


class AttemptConflict(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_code = "conflict"


class ReviewService:
    def __init__(self, policy: StepPolicy | None = None, rng: random.Random | None = None):
        self.policy = policy or StepPolicy()
        self.rng = rng or random.Random()

    def session(self, course: Course | None, kinds: list[str]) -> dict:
        due = self.policy.due(Term.objects.filter(course=course, deleted_at__isnull=True))
        terms = list(due.order_by("level", "created_at")[: settings.REVIEW_SESSION_SIZE])
        self.rng.shuffle(terms)
        rounds = [{"term": term, "kind": self.rng.choice(kinds)} for term in terms] if kinds else []

        return {"due": due.count(), "rounds": rounds}

    @transaction.atomic
    def record(self, user, data: dict) -> Term:
        terms = Term.objects.select_for_update().filter(user=user, deleted_at__isnull=True)
        term = terms.filter(pk=data["term"]).first()
        if term is None:
            raise Http404

        repeated = ReviewAttempt.objects.filter(pk=data["id"]).first()
        if repeated is not None:
            if repeated.term_id != term.pk:
                raise AttemptConflict("Esse id já está em uso.")
            return term

        exercise = None
        if data.get("exercise"):
            exercises = Exercise.objects.filter(term=term, kind=data["kind"])
            exercise = exercises.filter(pk=data["exercise"]).first()
            if exercise is None:
                raise serializers.ValidationError(
                    {"exercise": ["Esse exercício não é desse termo."]}
                )
            exercises.filter(pk=exercise.pk).update(served_count=F("served_count") + 1)

        term.level = self.policy.level_after(term.level, data["outcome"])
        term.save(update_fields=["level"])
        ReviewAttempt.objects.create(
            id=data["id"],
            term=term,
            exercise=exercise,
            kind=data["kind"],
            outcome=data["outcome"],
            level=term.level,
        )

        return term
