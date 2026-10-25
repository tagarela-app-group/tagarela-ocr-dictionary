from django.test import TestCase
from django.utils import timezone

from apps.captures.tests.helpers import make_user
from apps.vocabulary.models import Term
from apps.vocabulary.services import VocabularyService
from apps.vocabulary.tests.helpers import make_group, make_term


class AddTermsTests(TestCase):
    def setUp(self):
        self.user = make_user()

    def texts(self):
        return sorted(Term.objects.filter(user=self.user).values_list("text", flat=True))

    def test_new_terms_enter_ungrouped_with_their_kind(self):
        VocabularyService().add_terms(self.user, ["gap", "mind the  gap"])

        self.assertEqual(self.texts(), ["gap", "mind the gap"])
        terms = {t.text: t for t in Term.objects.all()}
        self.assertEqual(terms["gap"].kind, Term.Kind.WORD)
        self.assertEqual(terms["mind the gap"].kind, Term.Kind.EXPRESSION)
        self.assertIsNone(terms["gap"].group)
        self.assertEqual(terms["gap"].level, 0)

    def test_term_already_in_the_vocabulary_does_not_enter_again(self):
        travel = make_group(self.user)
        make_term(self.user, "Jet lag", travel)

        VocabularyService().add_terms(self.user, ["jet  LAG", "layover", "Layover"])

        self.assertEqual(self.texts(), ["Jet lag", "layover"])
        self.assertEqual(Term.objects.get(text="Jet lag").group, travel)

    def test_same_term_from_another_user_still_enters(self):
        make_term(make_user("bia@example.com"), "jet lag")

        VocabularyService().add_terms(self.user, ["jet lag"])

        self.assertEqual(self.texts(), ["jet lag"])

    def test_deleted_term_enters_again_as_new(self):
        make_term(self.user, "jet lag", make_group(self.user), level=3, deleted_at=timezone.now())

        VocabularyService().add_terms(self.user, ["Jet lag"])

        term = Term.objects.get(user=self.user)
        self.assertEqual((term.text, term.group, term.level), ("Jet lag", None, 0))
        self.assertIsNone(term.deleted_at)
