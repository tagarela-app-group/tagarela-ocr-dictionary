from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta

from django.conf import settings

REAL_DAY_SECONDS = 86400
SCALED_EPOCH = 1_750_000_000


def scaled() -> bool:
    return settings.REVIEW_SECONDS_PER_DAY != REAL_DAY_SECONDS


def days_between(start: datetime, end: datetime) -> float:
    return (end - start).total_seconds() / settings.REVIEW_SECONDS_PER_DAY


def after(start: datetime, days: float) -> datetime:
    return start + timedelta(seconds=days * settings.REVIEW_SECONDS_PER_DAY)


@dataclass(frozen=True)
class Day:
    date: date
    start: datetime
    end: datetime


def _scaled_date(moment: datetime) -> date:
    return date.fromordinal(
        1 + int((moment.timestamp() - SCALED_EPOCH) // settings.REVIEW_SECONDS_PER_DAY)
    )


def day_on(on: date, offset_minutes: int) -> Day:
    if scaled():
        start = datetime.fromtimestamp(
            SCALED_EPOCH + (on.toordinal() - 1) * settings.REVIEW_SECONDS_PER_DAY, UTC
        )
    else:
        start = datetime.combine(on, time.min, UTC) - timedelta(minutes=offset_minutes)

    return Day(on, start, after(start, 1))


def today(now: datetime, given: date | None, offset_minutes: int) -> Day:
    return day_on(local_date(now, given), offset_minutes)


def local_date(moment: datetime, given: date | None) -> date:
    if scaled():
        return _scaled_date(moment)

    return given or moment.astimezone(UTC).date()
