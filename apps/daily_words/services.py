from datetime import date

from django.conf import settings
from django.http import Http404
from django.utils import timezone

from apps.cards.services import ANALYSIS_LANGUAGES
from apps.common.schema import json_schema
from apps.common.text import clean_text, term_key
from apps.courses.models import Course
from apps.daily_words.models import DailyWord
from apps.daily_words.prompts import PROMPT_VERSION, SYSTEM_PROMPT, build_daily_word_input
from apps.daily_words.serializers import GeneratedWordSerializer
from apps.language_analysis.providers.gemini import GeminiInvalidResponseError, GeminiProvider
from apps.vocabulary.models import Term
from apps.vocabulary.services import VocabularyService

WORD_SCHEMA = json_schema(GeneratedWordSerializer())


class DailyWordService:
    def __init__(
        self, provider: GeminiProvider | None = None, vocabulary: VocabularyService | None = None
    ):
        self.provider = provider or GeminiProvider()
        self.vocabulary = vocabulary or VocabularyService()

    def today(self, course: Course | None) -> DailyWord:
        if course is None:
            raise Http404

        day = timezone.localdate()
        word = DailyWord.objects.filter(course=course, date=day).first()
        word = word or self._generate(course, day)
        word.term = self._term(word)

        return word

    def save(self, course: Course | None) -> DailyWord:
        word = self.today(course)
        self.vocabulary.add_terms(word.course, [word.text])
        word.term = self._term(word)

        return word

    def _term(self, word: DailyWord) -> Term | None:
        terms = Term.objects.filter(course=word.course, deleted_at__isnull=True)

        return terms.filter(key=term_key(word.text)).first()

    def _generate(self, course: Course, day: date) -> DailyWord:
        generated = GeneratedWordSerializer(
            data=self.provider.generate(
                build_daily_word_input(
                    {
                        "source_language": ANALYSIS_LANGUAGES[course.learning],
                        "target_language": ANALYSIS_LANGUAGES[course.base],
                        "avoid": self._avoid(course),
                    }
                ),
                system_instruction=SYSTEM_PROMPT,
                schema=WORD_SCHEMA,
            )
        )
        if not generated.is_valid():
            raise GeminiInvalidResponseError

        text = clean_text(generated.validated_data["source_word"])
        word, _ = DailyWord.objects.get_or_create(
            course=course,
            date=day,
            defaults={
                "text": text,
                "kind": Term.Kind.EXPRESSION if " " in text else Term.Kind.WORD,
                "phonetic": generated.validated_data["phonetic"],
                "example": generated.validated_data["source_example"],
                "meaning": generated.validated_data["target_meaning"],
                "prompt_version": PROMPT_VERSION,
                "model": settings.GEMINI_MODEL,
            },
        )

        return word

    def _avoid(self, course: Course) -> list[str]:
        limit = settings.DAILY_WORD_AVOID_LIMIT
        terms = Term.objects.filter(course=course).values_list("text", flat=True)[:limit]
        past = DailyWord.objects.filter(course=course).values_list("text", flat=True)[:limit]

        return [*past, *terms]
