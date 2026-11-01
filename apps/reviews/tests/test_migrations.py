from datetime import timedelta

from django.utils import timezone

from apps.common.tests.migrations import MigrationTestCase

ACCOUNTS = ("accounts", "0002_user_country")
BEFORE = [
    ACCOUNTS,
    ("courses", "0001_initial"),
    ("vocabulary", "0008_grupo_sem_usuario"),
    ("reviews", "0001_initial"),
]
AFTER = [
    ACCOUNTS,
    ("courses", "0002_capacidade_de_revisao"),
    ("vocabulary", "0011_nivel_vem_do_prazo"),
    ("reviews", "0003_preenche_tentativas_antigas"),
]


class MemoryMigrationTests(MigrationTestCase):
    def setUp(self):
        super().setUp()
        apps = self.migrate(*BEFORE)
        user = apps.get_model("accounts", "User").objects.create(email="ana@example.com")
        course = apps.get_model("courses", "Course").objects.create(
            user=user, learning="en", base="pt", active=True
        )
        Term = apps.get_model("vocabulary", "Term")
        self.terms = {
            level: Term.objects.create(
                user=user,
                course=course,
                text=f"term {level}",
                key=f"term {level}",
                kind="word",
                level=level,
            ).pk
            for level in range(6)
        }
        self.apps = apps

    def test_interval_comes_from_the_old_level_and_read_terms_are_due_now(self):
        apps = self.migrate(*AFTER)

        Term = apps.get_model("vocabulary", "Term")
        now = timezone.now()
        for level, interval in {1: 4, 2: 8, 3: 16, 4: 24, 5: 32}.items():
            term = Term.objects.get(pk=self.terms[level])
            self.assertEqual(term.interval_days, interval)
            self.assertEqual(term.scheduled_days, interval)
            self.assertLessEqual(term.due_at, now)
            self.assertIsNotNone(term.first_read_at)
            self.assertAlmostEqual(
                (now - term.last_session_at) / timedelta(days=1), interval, delta=0.01
            )

    def test_level_zero_stays_new(self):
        apps = self.migrate(*AFTER)

        term = apps.get_model("vocabulary", "Term").objects.get(pk=self.terms[0])
        self.assertEqual(term.interval_days, 2)
        self.assertIsNone(term.due_at)
        self.assertIsNone(term.first_read_at)

    def test_old_attempts_get_their_date_and_role(self):
        Term = self.apps.get_model("vocabulary", "Term")
        attempt = self.apps.get_model("reviews", "ReviewAttempt").objects.create(
            term=Term.objects.get(pk=self.terms[1]),
            kind="listen_write",
            outcome="first",
            level=1,
        )

        apps = self.migrate(*AFTER)

        saved = apps.get_model("reviews", "ReviewAttempt").objects.get(pk=attempt.pk)
        self.assertEqual(saved.role, "session")
        self.assertEqual(saved.played_at, attempt.created_at)
        self.assertEqual(saved.local_date, timezone.localdate(attempt.created_at))
