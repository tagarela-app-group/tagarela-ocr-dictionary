import random
from dataclasses import dataclass
from datetime import date, datetime

from django.conf import settings
from django.db import transaction
from django.db.models import F, Min, QuerySet
from django.http import Http404
from django.utils import timezone
from rest_framework import serializers, status
from rest_framework.exceptions import APIException

from apps.courses.models import Course
from apps.exercises.kinds import KINDS
from apps.exercises.models import Exercise
from apps.reviews import clock, policy
from apps.reviews.models import ReviewAttempt
from apps.vocabulary.models import Term

SESSION_ROLES = (ReviewAttempt.Role.FIRST_REVIEW, ReviewAttempt.Role.SESSION)


class AttemptConflict(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_code = "conflict"


@dataclass(frozen=True)
class Plan:
    retests: list[Term]
    overdue: list[Term]
    first_reviews: list[Term]
    done: int
    waiting: int


class ReviewService:
    def __init__(self, rng: random.Random | None = None):
        self.rng = rng or random.Random()

    def session(
        self, course: Course | None, kinds: list[str], on: date | None = None, offset: int = 0
    ) -> dict:
        if course is None:
            return {
                "due": 0,
                "limit": 0,
                "done": 0,
                "waiting": 0,
                "unread": 0,
                "next_due_at": None,
                "rounds": [],
            }

        now = timezone.now()
        day = clock.today(now, on, offset)
        with transaction.atomic():
            course = Course.objects.select_for_update().get(pk=course.pk)
            self._open_day(course, day, offset)
            plan = self._plan(course, day, now)

        retests = {term.pk for term in plan.retests}
        terms = [*plan.retests, *plan.overdue, *plan.first_reviews]
        rounds = []
        if kinds:
            rounds = [
                {"term": term, "kind": self.rng.choice(kinds), "retest": term.pk in retests}
                for term in terms[: settings.REVIEW_SESSION_SIZE]
            ]

        studied = self._terms(course)
        return {
            "due": len(terms),
            "limit": course.daily_limit,
            "done": plan.done,
            "waiting": plan.waiting,
            "unread": studied.filter(first_read_at__isnull=True).count(),
            "next_due_at": studied.filter(due_at__gt=now).aggregate(Min("due_at"))["due_at__min"],
            "rounds": rounds,
        }

    def ask_for_more(self, course: Course | None) -> None:
        if course is not None:
            Course.objects.filter(pk=course.pk).update(
                daily_limit=F("daily_limit") + settings.REVIEW_SESSION_SIZE
            )

    @transaction.atomic
    def study(self, user, term_id, event: str) -> Term:
        term = self._locked_term(user, term_id)
        now = timezone.now()
        if event == "read" and term.first_read_at is None:
            term.first_read_at = now
            term.study_points += settings.REVIEW_CARD_POINTS
            if term.last_session_at is None:
                term.scheduled_days = settings.REVIEW_FIRST_REVIEW_DAYS
                term.due_at = clock.after(now, term.scheduled_days)
            term.save()
        elif event == "listened" and term.audio_heard_at is None:
            term.audio_heard_at = now
            term.study_points += settings.REVIEW_CARD_POINTS
            term.save()

        return term

    @transaction.atomic
    def record(self, user, data: dict) -> ReviewAttempt:
        term = self._locked_term(user, data["term"])

        repeated = ReviewAttempt.objects.filter(pk=data["id"]).first()
        if repeated is not None:
            if repeated.term_id != term.pk:
                raise AttemptConflict("Esse id já está em uso.")
            return repeated

        exercise = None
        seen = False
        if data.get("exercise"):
            exercises = Exercise.objects.filter(term=term, kind=data["kind"])
            exercise = exercises.filter(pk=data["exercise"]).first()
            if exercise is None:
                raise serializers.ValidationError(
                    {"exercise": ["Esse exercício não é desse termo."]}
                )
            seen = ReviewAttempt.objects.filter(exercise=exercise).exists()
            exercises.filter(pk=exercise.pk).update(served_count=F("served_count") + 1)

        now = timezone.now()
        played_at = min(data.get("played_at", now), now)
        local_date = clock.local_date(played_at, data.get("local_date"))
        role = self._role(term, played_at, local_date)
        result = policy.score(
            policy.Play(
                effort=KINDS[data["kind"]].effort,
                outcome=data["outcome"],
                seen_sentence=seen,
                used_slow=data["used_slow"],
                study_points=term.study_points if role in SESSION_ROLES else 0,
            )
        )
        level_before = term.level
        interval_before = term.interval_days
        if role in SESSION_ROLES:
            self._apply_session(term, result, played_at)
        elif role == ReviewAttempt.Role.RETEST:
            self._apply_retest(term, played_at)

        return ReviewAttempt.objects.create(
            id=data["id"],
            term=term,
            exercise=exercise,
            kind=data["kind"],
            outcome=data["outcome"],
            role=role,
            played_at=played_at,
            local_date=local_date,
            seen_sentence=seen,
            used_slow=data["used_slow"],
            errors=data["errors"],
            hints=data["hints"],
            audio_replays=data["audio_replays"],
            response_ms=data.get("response_ms"),
            points=result.points,
            level_before=level_before,
            level=term.level,
            interval_before=interval_before,
            interval_days=term.interval_days,
            due_at=term.due_at,
        )

    def _locked_term(self, user, term_id) -> Term:
        terms = Term.objects.select_for_update().filter(user=user, deleted_at__isnull=True)
        term = terms.filter(pk=term_id).first()
        if term is None:
            raise Http404

        return term

    def _terms(self, course: Course) -> QuerySet[Term]:
        return Term.objects.filter(course=course, deleted_at__isnull=True)

    def _role(self, term: Term, played_at: datetime, local_date: date) -> str:
        if term.last_session_at is not None and played_at < term.last_session_at:
            return ReviewAttempt.Role.EXTRA

        same_day = ReviewAttempt.objects.filter(term=term, local_date=local_date)
        session = same_day.filter(role__in=SESSION_ROLES).first()
        if session is None:
            if term.last_session_at is None:
                return ReviewAttempt.Role.FIRST_REVIEW
            return ReviewAttempt.Role.SESSION

        retested = same_day.filter(role=ReviewAttempt.Role.RETEST).exists()
        if policy.went_badly(session.points) and not retested and played_at >= term.due_at:
            return ReviewAttempt.Role.RETEST

        return ReviewAttempt.Role.EXTRA

    def _apply_session(self, term: Term, result: policy.Score, played_at: datetime) -> None:
        since = term.last_session_at or term.first_read_at or played_at
        time = policy.time_factor(clock.days_between(since, played_at), term.scheduled_days)
        term.interval_days = policy.new_interval(term.interval_days, result.points, term.ease, time)
        term.ease = policy.next_ease(term.ease, result.points_without_support)
        wait = policy.wait_days(term.interval_days, result.points, self.rng)
        term.scheduled_days = (
            settings.REVIEW_FIRST_REVIEW_DAYS if policy.went_badly(result.points) else wait
        )
        term.due_at = clock.after(played_at, wait)
        term.last_session_at = played_at
        term.first_read_at = term.first_read_at or played_at
        term.study_points = 0
        term.save()

    def _apply_retest(self, term: Term, played_at: datetime) -> None:
        term.scheduled_days = settings.REVIEW_FIRST_REVIEW_DAYS
        term.due_at = clock.after(played_at, term.scheduled_days)
        term.save()

    def _open_day(self, course: Course, day: clock.Day, offset: int) -> None:
        last = course.last_active_on
        if last == day.date or (last is not None and last > day.date):
            return

        if last is not None:
            previous = clock.day_on(last, offset)
            plan = self._plan(course, previous, previous.end)
            course.review_capacity = policy.capacity_after(
                course.review_capacity,
                left=len(plan.overdue) + len(plan.first_reviews),
                done=plan.done,
                waiting=plan.waiting,
            )
        course.daily_limit = course.review_capacity
        course.last_active_on = day.date
        course.save(update_fields=["review_capacity", "daily_limit", "last_active_on"])

    def _plan(self, course: Course, day: clock.Day, now: datetime) -> Plan:
        attempts = ReviewAttempt.objects.filter(term__course=course, local_date=day.date)
        sessions = attempts.filter(role__in=SESSION_ROLES)
        done = {attempt.term_id for attempt in sessions}
        retested = set(
            attempts.filter(role=ReviewAttempt.Role.RETEST).values_list("term_id", flat=True)
        )
        badly = {
            attempt.term_id
            for attempt in sessions
            if policy.went_badly(attempt.points) and attempt.term_id not in retested
        }

        studied = self._terms(course).filter(first_read_at__isnull=False)
        retests = list(studied.filter(pk__in=badly, due_at__lte=now).order_by("due_at"))
        reviewed = studied.filter(last_session_at__isnull=False)
        overdue_pool = sorted(
            reviewed.filter(due_at__lt=day.end).exclude(pk__in=done),
            key=lambda term: clock.days_between(term.last_session_at, now) / term.scheduled_days,
            reverse=True,
        )
        first_pool = list(
            studied.filter(last_session_at__isnull=True, due_at__lt=day.end).order_by(
                "first_read_at"
            )
        )

        room = max(0, course.daily_limit - len(done))
        overdue = overdue_pool[:room]
        horizon = clock.after(now, settings.REVIEW_FORECAST_DAYS)
        forecast = reviewed.filter(due_at__lt=horizon).count() / settings.REVIEW_FORECAST_DAYS
        asked_for_more = course.daily_limit - course.review_capacity
        slots = (
            policy.first_review_slots(course.review_capacity, forecast)
            + asked_for_more
            - sessions.filter(role=ReviewAttempt.Role.FIRST_REVIEW).count()
        )
        first_reviews = first_pool[: max(0, min(slots, room - len(overdue)))]

        return Plan(
            retests=retests,
            overdue=overdue,
            first_reviews=first_reviews,
            done=len(done),
            waiting=len(overdue_pool) + len(first_pool) - len(overdue) - len(first_reviews),
        )
