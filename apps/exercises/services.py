import random

from django.conf import settings
from django.http import Http404

from apps.cards.models import TermCard
from apps.cards.services import ANALYSIS_LANGUAGES
from apps.exercises.kinds import KINDS, Brief
from apps.exercises.models import Exercise
from apps.language_analysis.providers.gemini import (
    GeminiInvalidResponseError,
    GeminiProvider,
)
from apps.vocabulary.models import Term


class ExerciseService:
    def __init__(self, provider: GeminiProvider | None = None, rng: random.Random | None = None):
        self.provider = provider or GeminiProvider()
        self.rng = rng or random.Random()

    def exercises(self, user, term_id, kind: str) -> list[Exercise]:
        if kind not in KINDS:
            raise Http404

        terms = Term.objects.select_related("course").filter(user=user, deleted_at__isnull=True)
        term = terms.filter(pk=term_id).first()
        if term is None:
            raise Http404

        exercises = self._stored(term, kind) or self._generate(term, kind)
        served = KINDS[kind].serve(term, [exercise.payload for exercise in exercises], self.rng)
        for exercise, payload in zip(exercises, served, strict=True):
            exercise.payload = payload

        return exercises

    def _stored(self, term: Term, kind: str) -> list[Exercise]:
        return list(Exercise.objects.filter(term=term, kind=kind))

    def _generate(self, term: Term, kind: str) -> list[Exercise]:
        exercise_kind = KINDS[kind]
        count = settings.EXERCISE_VARIATIONS
        response = self.provider.generate(
            exercise_kind.build_input(self._brief(term, count)),
            system_instruction=exercise_kind.system_prompt,
            schema=exercise_kind.response_schema(count),
        )
        payloads = exercise_kind.payloads(response)[:count]
        if not payloads:
            raise GeminiInvalidResponseError

        Exercise.objects.bulk_create(
            [
                Exercise(
                    term=term,
                    kind=kind,
                    variant=variant,
                    payload=payload,
                    prompt_version=exercise_kind.prompt_version,
                    model=settings.GEMINI_MODEL,
                )
                for variant, payload in enumerate(payloads)
            ],
            ignore_conflicts=True,
        )

        return self._stored(term, kind)

    def _brief(self, term: Term, count: int) -> Brief:
        card = TermCard.objects.filter(term=term).first()
        analysis = card.analysis if card else {}
        meaning = analysis.get("source_meaning_in_context") or analysis.get("meaning_in_context")

        return Brief(
            focus=term.text,
            focus_kind=term.kind,
            source_language=ANALYSIS_LANGUAGES[term.course.learning],
            target_language=ANALYSIS_LANGUAGES[term.course.base],
            meaning=meaning or None,
            count=count,
        )
