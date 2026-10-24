from importlib import import_module

from django.apps import apps
from django.test import TestCase
from django.utils import timezone

from apps.captures.models import Capture, CaptureTerm
from apps.captures.tests.helpers import make_capture, make_user
from apps.vocabulary.models import Term
from apps.vocabulary.tests.helpers import make_term

backfill = import_module("apps.vocabulary.migrations.0002_termos_das_capturas_analisadas")


class AnalyzedCaptureTermsTests(TestCase):
    def test_terms_of_analyzed_captures_enter_once(self):
        user = make_user()
        make_term(user, "train")
        analyzed = {"status": Capture.Status.ANALYZED, "analyzed_at": timezone.now()}
        first = make_capture(user, **analyzed)
        CaptureTerm.objects.create(capture=first, text="Mind", start=7, end=11)
        CaptureTerm.objects.create(capture=first, text="train", start=32, end=37)
        cleared = make_capture(user, **analyzed, discarded_at=timezone.now())
        CaptureTerm.objects.create(capture=cleared, text="mind", start=7, end=11)
        CaptureTerm.objects.create(capture=cleared, text="gap", start=16, end=19)
        ready = make_capture(user)
        CaptureTerm.objects.create(capture=ready, text="platform", start=48, end=56)

        backfill.fill(apps, None)

        texts = sorted(Term.objects.values_list("text", flat=True))
        self.assertEqual(texts, ["Mind", "gap", "train"])
