from django.db.models import QuerySet

from apps.reviews.models import ReviewAttempt
from apps.vocabulary.models import Term

MASTERED_LEVEL = 5


class StepPolicy:
    def due(self, terms: QuerySet[Term]) -> QuerySet[Term]:
        return terms.filter(level__lt=MASTERED_LEVEL)

    def level_after(self, level: int, outcome: str) -> int:
        if outcome == ReviewAttempt.Outcome.MISSED:
            return level

        return min(MASTERED_LEVEL, level + 1)
