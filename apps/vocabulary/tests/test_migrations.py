from django.utils import timezone

from apps.captures.models import Capture
from apps.common.tests.migrations import MigrationTestCase
from apps.courses.models import Course
from apps.vocabulary.models import Group, Term

ACCOUNTS = ("accounts", "0002_user_country")


class AnalyzedCaptureTermsTests(MigrationTestCase):
    def test_terms_of_analyzed_captures_enter_once(self):
        apps = self.migrate(
            ACCOUNTS,
            ("vocabulary", "0001_inicial"),
            ("captures", "0002_sem_processamento_no_servidor"),
        )
        User = apps.get_model("accounts", "User")
        Capture = apps.get_model("captures", "Capture")
        CaptureTerm = apps.get_model("captures", "CaptureTerm")
        OldTerm = apps.get_model("vocabulary", "Term")
        user = User.objects.create(email="ana@example.com")
        OldTerm.objects.create(user=user, text="train", key="train", kind="word")

        def capture(**fields):
            return Capture.objects.create(
                id=f"00000000-0000-4000-8000-00000000000{Capture.objects.count()}",
                user=user,
                source="text",
                captured_at=timezone.now(),
                **fields,
            )

        first = capture(status="analyzed", analyzed_at=timezone.now())
        CaptureTerm.objects.create(capture=first, text="Mind", start=7, end=11)
        CaptureTerm.objects.create(capture=first, text="train", start=32, end=37)
        cleared = capture(
            status="analyzed", analyzed_at=timezone.now(), discarded_at=timezone.now()
        )
        CaptureTerm.objects.create(capture=cleared, text="mind", start=7, end=11)
        CaptureTerm.objects.create(capture=cleared, text="gap", start=16, end=19)
        ready = capture(status="ready")
        CaptureTerm.objects.create(capture=ready, text="platform", start=48, end=56)

        apps = self.migrate(ACCOUNTS, ("vocabulary", "0002_termos_das_capturas_analisadas"))

        terms = apps.get_model("vocabulary", "Term").objects.values_list("text", flat=True)
        self.assertEqual(sorted(terms), ["Mind", "gap", "train"])


class CourseBackfillTests(MigrationTestCase):
    def test_current_study_becomes_english_through_portuguese(self):
        apps = self.migrate(
            ACCOUNTS,
            ("vocabulary", "0005_curso_nos_termos_e_grupos"),
            ("captures", "0003_curso_nas_capturas"),
        )
        User = apps.get_model("accounts", "User")
        ana = User.objects.create(email="ana@example.com")
        bia = User.objects.create(email="bia@example.com")
        User.objects.create(email="caio@example.com")
        group = apps.get_model("vocabulary", "Group").objects.create(
            user=ana, name="Viagem", icon="travel", accent="sky"
        )
        OldTerm = apps.get_model("vocabulary", "Term")
        OldTerm.objects.create(user=ana, group=group, text="layover", key="layover", kind="word")
        OldTerm.objects.create(user=bia, text="gap", key="gap", kind="word")
        apps.get_model("captures", "Capture").objects.create(
            id="00000000-0000-4000-8000-000000000001",
            user=bia,
            source="text",
            status="ready",
            captured_at=timezone.now(),
        )

        self.migrate(
            ("vocabulary", "0007_curso_obrigatorio"), ("captures", "0005_curso_obrigatorio")
        )

        courses = Course.objects.order_by("user__email")
        self.assertEqual(
            [(c.user.email, c.learning, c.base, c.active) for c in courses],
            [("ana@example.com", "en", "pt", True), ("bia@example.com", "en", "pt", True)],
        )
        self.assertEqual(Group.objects.get().course.user.email, "ana@example.com")
        self.assertEqual(
            {t.text: t.course.user.email for t in Term.objects.all()},
            {"layover": "ana@example.com", "gap": "bia@example.com"},
        )
        self.assertEqual(
            Capture.objects.get().course, Course.objects.get(user__email="bia@example.com")
        )
