from django.conf import settings
from django.http import Http404

from apps.captures.models import Capture
from apps.cards.models import TermCard
from apps.language_analysis.services import LinguisticAnalysisService
from apps.vocabulary.models import Term
from apps.vocabulary.services import term_key

ANALYSIS_LANGUAGES = {"en": "en", "es": "es", "pt": "pt-BR"}


class TermCardService:
    def __init__(self, analysis: LinguisticAnalysisService | None = None):
        self.analysis = analysis or LinguisticAnalysisService()

    def detail(self, user, term_id) -> dict:
        term = self._term(user, term_id)
        captures = self._captures(term)
        card = TermCard.objects.filter(term=term).first() or self._generate(term, captures)

        return {"term": term, "card": card, "captures": captures}

    def reveal(self, user, term_id, revealed: bool) -> dict:
        term = self._term(user, term_id)
        card = TermCard.objects.filter(term=term).first()
        if card is None:
            raise Http404

        card.revealed = revealed
        card.save(update_fields=["revealed", "updated_at"])

        return {"term": term, "card": card, "captures": self._captures(term)}

    def _term(self, user, term_id) -> Term:
        terms = Term.objects.select_related("course", "group")
        term = terms.filter(user=user, deleted_at__isnull=True, pk=term_id).first()
        if term is None:
            raise Http404

        return term

    def _captures(self, term: Term) -> list[Capture]:
        captures = list(
            Capture.objects.filter(
                course=term.course,
                status=Capture.Status.ANALYZED,
                discarded_at__isnull=True,
                terms__text__iexact=term.text,
            )
            .distinct()
            .order_by("-captured_at")
            .prefetch_related("terms")[: settings.TERM_CARD_MAX_CAPTURES]
        )
        spans = [span for capture in captures for span in capture.terms.all()]
        ids = dict(
            Term.objects.filter(
                course=term.course,
                deleted_at__isnull=True,
                key__in={term_key(span.text) for span in spans},
            ).values_list("key", "id")
        )
        for span in spans:
            span.term_id = ids.get(term_key(span.text))

        return captures

    def _generate(self, term: Term, captures: list[Capture]) -> TermCard:
        context = captures[0].text if captures else term.text
        result = self.analysis.analyze(
            {
                "text": context[: settings.LANGUAGE_ANALYSIS_MAX_TEXT_LENGTH],
                "selected_term": term.text,
                "source_language": ANALYSIS_LANGUAGES[term.course.learning],
                "target_language": ANALYSIS_LANGUAGES[term.course.base],
                "level": None,
            }
        )
        card, _ = TermCard.objects.update_or_create(
            term=term,
            defaults={
                "analysis": result["analysis"],
                "prompt_version": result["metadata"]["prompt_version"],
                "model": result["metadata"]["model"],
            },
        )
        term.translation = (result["analysis"]["translation"] or "")[:255]
        term.save(update_fields=["translation"])

        return card
