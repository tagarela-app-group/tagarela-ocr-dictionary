import random
from dataclasses import dataclass

from django.conf import settings

from apps.exercises.kinds import Effort
from apps.reviews.models import ReviewAttempt

HOURS_PER_DAY = 24


@dataclass(frozen=True)
class Play:
    effort: str
    outcome: str
    seen_sentence: bool
    used_slow: bool
    study_points: float


@dataclass(frozen=True)
class Score:
    points: float
    points_without_support: float


def score(play: Play) -> Score:
    base = {
        Effort.READ: settings.REVIEW_POINTS_READ,
        Effort.LISTEN: settings.REVIEW_POINTS_LISTEN,
        Effort.PRODUCE: settings.REVIEW_POINTS_PRODUCE,
    }[play.effort]
    result = {
        ReviewAttempt.Outcome.FIRST: settings.REVIEW_RESULT_FIRST,
        ReviewAttempt.Outcome.SLIP: settings.REVIEW_RESULT_SLIP,
        ReviewAttempt.Outcome.HINT: settings.REVIEW_RESULT_HINT,
        ReviewAttempt.Outcome.RETRY: settings.REVIEW_RESULT_RETRY,
        ReviewAttempt.Outcome.MISSED: settings.REVIEW_RESULT_MISSED,
    }[play.outcome]
    context = settings.REVIEW_SEEN_SENTENCE if play.seen_sentence else 1
    support = settings.REVIEW_SLOW_SUPPORT if play.used_slow else 1
    plain = base * result * context

    return Score(
        points=plain * support + play.study_points,
        points_without_support=plain + play.study_points,
    )


def rating(points: float) -> str:
    if points < settings.REVIEW_FAIR_POINTS:
        return "poor"
    if points < settings.REVIEW_GOOD_POINTS:
        return "fair"
    if points < settings.REVIEW_GREAT_POINTS:
        return "good"

    return "great"


def went_badly(points: float) -> bool:
    return points < settings.REVIEW_FAIR_POINTS


def growth(points: float) -> float:
    xs = settings.REVIEW_GROWTH_POINTS
    ys = settings.REVIEW_GROWTH_FACTORS
    if points <= xs[0]:
        return ys[0]
    for (x0, y0), (x1, y1) in zip(zip(xs, ys), zip(xs[1:], ys[1:]), strict=False):
        if points <= x1:
            return y0 + (points - x0) / (x1 - x0) * (y1 - y0)

    return ys[-1]


def time_factor(elapsed_days: float, scheduled_days: float) -> float:
    ratio = elapsed_days / scheduled_days
    return min(settings.REVIEW_TIME_MAX, max(settings.REVIEW_TIME_MIN, ratio))


def new_interval(interval: float, points: float, ease: float, time: float) -> float:
    factor = growth(points)
    if factor > 1:
        factor = min(settings.REVIEW_MAX_GROWTH, 1 + (factor - 1) * ease * time)

    return min(
        settings.REVIEW_MAX_INTERVAL_DAYS, max(settings.REVIEW_MIN_INTERVAL_DAYS, interval * factor)
    )


def next_ease(ease: float, points_without_support: float) -> float:
    if points_without_support < settings.REVIEW_FAIR_POINTS:
        ease -= settings.REVIEW_EASE_DROP
    elif points_without_support >= settings.REVIEW_GOOD_POINTS:
        ease += settings.REVIEW_EASE_GAIN

    return min(settings.REVIEW_EASE_MAX, max(settings.REVIEW_EASE_MIN, ease))


def wait_days(interval: float, points: float, rng: random.Random) -> float:
    if went_badly(points):
        hours = settings.REVIEW_RETEST_BASE_HOURS + settings.REVIEW_RETEST_HOURS_PER_POINT * points
        return hours / HOURS_PER_DAY

    jitter = settings.REVIEW_JITTER
    return interval * rng.uniform(1 - jitter, 1 + jitter)


def first_review_slots(capacity: int, forecast_per_day: float) -> int:
    return int(max(1, min(capacity - forecast_per_day, capacity / 4)))


def capacity_after(capacity: int, left: int, done: int, waiting: int) -> int:
    if left > 0:
        capacity -= settings.REVIEW_CAPACITY_DOWN
    elif done > 0 and waiting > 0:
        capacity += settings.REVIEW_CAPACITY_UP

    return min(settings.REVIEW_CAPACITY_MAX, max(settings.REVIEW_CAPACITY_MIN, capacity))
