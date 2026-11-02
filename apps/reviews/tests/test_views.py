import uuid
from datetime import UTC, timedelta
from itertools import pairwise

from django.test import SimpleTestCase, override_settings
from django.utils import timezone
from rest_framework.test import APITestCase

from apps.captures.tests.helpers import make_user
from apps.courses.models import Course
from apps.courses.tests.helpers import make_course
from apps.exercises.models import Exercise
from apps.reviews import clock
from apps.reviews.models import ReviewAttempt
from apps.vocabulary.tests.helpers import api_datetime, make_term


def make_exercise(term, variant: int = 0) -> Exercise:
    return Exercise.objects.create(
        term=term,
        kind=Exercise.Kind.LISTEN_WRITE,
        variant=variant,
        payload={"sentence": term.text},
        prompt_version="1.0",
        model="m",
    )


def days_ago(days: float):
    return timezone.now() - timedelta(days=days)


def first_review_term(user, text: str, course, read_days_ago: float = 2, **fields):
    return make_term(
        user,
        text,
        course=course,
        first_read_at=days_ago(read_days_ago),
        due_at=days_ago(read_days_ago - 1),
        **fields,
    )


def reviewed_term(user, text: str, course, overdue_days: float = 1, scheduled: float = 8, **fields):
    return make_term(
        user,
        text,
        course=course,
        **{
            "first_read_at": days_ago(30),
            "last_session_at": days_ago(scheduled + overdue_days),
            "scheduled_days": scheduled,
            "due_at": days_ago(overdue_days),
            "interval_days": 8.0,
            **fields,
        },
    )


def local_today():
    return timezone.now().astimezone(UTC).date()


def attempted(term, on=None, role=ReviewAttempt.Role.SESSION, points: float = 15) -> ReviewAttempt:
    return ReviewAttempt.objects.create(
        term=term,
        kind=Exercise.Kind.LISTEN_WRITE,
        outcome=ReviewAttempt.Outcome.FIRST,
        role=role,
        played_at=timezone.now(),
        local_date=on or local_today(),
        points=points,
        level_before=0,
        level=0,
        interval_before=2,
        interval_days=2,
    )


class ReviewSessionTests(APITestCase):
    def setUp(self):
        super().setUp()
        self.user = make_user()
        self.client.force_authenticate(self.user)
        self.course = make_course(self.user)

    def session(self, query: str = "?kinds=listen_write"):
        response = self.client.get(f"/api/v1/reviews{query}")
        self.assertEqual(response.status_code, 200, response.content)
        return response.json()

    def texts(self, session) -> list[str]:
        return [round_["term"]["text"] for round_ in session["rounds"]]

    def test_only_terms_with_the_card_read_and_due_today_enter(self):
        due = reviewed_term(self.user, "on the fence", self.course)
        reviewed_term(self.user, "later", self.course, overdue_days=-3)
        make_term(self.user, "never read", course=self.course)
        gone = reviewed_term(self.user, "gone", self.course)
        gone.deleted_at = timezone.now()
        gone.save(update_fields=["deleted_at"])
        reviewed_term(self.user, "en las nubes", make_course(self.user, "es", "pt"))

        session = self.session()

        self.assertEqual(session["due"], 1)
        self.assertEqual(session["unread"], 1)
        self.assertEqual(
            session["rounds"],
            [
                {
                    "term": {
                        "id": str(due.id),
                        "text": "on the fence",
                        "translation": "",
                        "kind": "expression",
                        "level": 2,
                        "interval_days": 8.0,
                        "due_at": api_datetime(due.due_at),
                        "created_at": api_datetime(due.created_at),
                    },
                    "kind": "listen_write",
                    "retest": False,
                }
            ],
        )

    def test_order_is_retests_then_most_late_then_first_reviews(self):
        first_review_term(self.user, "first", self.course)
        reviewed_term(self.user, "a little late", self.course, overdue_days=1, scheduled=8)
        reviewed_term(self.user, "very late", self.course, overdue_days=8, scheduled=2)
        retest = reviewed_term(self.user, "retest", self.course, overdue_days=0.1)
        attempted(retest, points=1)

        session = self.session()

        self.assertEqual(self.texts(session), ["retest", "very late", "a little late", "first"])
        self.assertEqual([r["retest"] for r in session["rounds"]], [True, False, False, False])

    def test_due_later_today_on_the_device_already_counts(self):
        date = local_today() + timedelta(days=1)
        make_term(
            self.user,
            "tomorrow, before midnight",
            course=self.course,
            first_read_at=days_ago(1),
            due_at=clock.day_on(date, 0).end - timedelta(minutes=1),
        )
        make_term(
            self.user,
            "after midnight",
            course=self.course,
            first_read_at=days_ago(1),
            due_at=clock.day_on(date, 0).end + timedelta(minutes=1),
        )

        session = self.session(f"?kinds=listen_write&date={date}&offset=0")

        self.assertEqual(self.texts(session), ["tomorrow, before midnight"])

    def test_session_stops_at_the_daily_limit_and_counts_what_did_not_fit(self):
        Course.objects.filter(pk=self.course.pk).update(
            review_capacity=5, daily_limit=5, last_active_on=local_today()
        )
        for index in range(7):
            reviewed_term(self.user, f"term {index}", self.course)

        session = self.session()

        self.assertEqual((session["due"], session["waiting"], session["limit"]), (5, 2, 5))
        self.assertEqual(len(session["rounds"]), 5)

    def test_done_today_uses_up_the_limit_but_a_retest_does_not(self):
        Course.objects.filter(pk=self.course.pk).update(
            review_capacity=5, daily_limit=5, last_active_on=local_today()
        )
        for index in range(4):
            attempted(reviewed_term(self.user, f"done {index}", self.course, overdue_days=-5))
        retest = reviewed_term(self.user, "retest", self.course, overdue_days=0.1)
        attempted(retest, points=0)
        for index in range(3):
            reviewed_term(self.user, f"term {index}", self.course)

        session = self.session()

        self.assertEqual(session["done"], 5)
        self.assertEqual(self.texts(session), ["retest"])
        self.assertEqual(session["waiting"], 3)

    def test_only_one_retest_a_day(self):
        term = reviewed_term(self.user, "retest", self.course, overdue_days=0.1)
        attempted(term, points=0)
        attempted(term, role=ReviewAttempt.Role.RETEST, points=0)

        self.assertEqual(self.texts(self.session()), [])

    def test_retest_waits_for_its_hour(self):
        term = reviewed_term(self.user, "retest", self.course, overdue_days=-0.1)
        attempted(term, points=0)

        self.assertEqual(self.texts(self.session()), [])

    def test_term_reviewed_today_does_not_come_back_today(self):
        term = reviewed_term(self.user, "done", self.course)
        attempted(term, points=15)

        self.assertEqual(self.texts(self.session()), [])

    def test_first_reviews_are_limited_by_slots_oldest_read_first(self):
        Course.objects.filter(pk=self.course.pk).update(last_active_on=local_today())
        first_review_term(self.user, "newer", self.course, read_days_ago=2)
        first_review_term(self.user, "newest", self.course, read_days_ago=1.5)
        first_review_term(self.user, "oldest", self.course, read_days_ago=3)

        session = self.session()

        self.assertEqual(self.texts(session), ["oldest", "newer"])
        self.assertEqual(session["waiting"], 1)

    def test_busy_forecast_leaves_a_single_first_review(self):
        Course.objects.filter(pk=self.course.pk).update(last_active_on=local_today())
        for index in range(70):
            reviewed_term(self.user, f"soon {index}", self.course, overdue_days=-2)
        first_review_term(self.user, "a", self.course, read_days_ago=3)
        first_review_term(self.user, "b", self.course, read_days_ago=2)

        self.assertEqual(self.texts(self.session()), ["a"])

    def test_first_review_done_today_uses_its_slot(self):
        Course.objects.filter(pk=self.course.pk).update(last_active_on=local_today())
        for index in range(2):
            term = reviewed_term(self.user, f"done {index}", self.course, overdue_days=-5)
            attempted(term, role=ReviewAttempt.Role.FIRST_REVIEW)
        first_review_term(self.user, "waiting", self.course)

        session = self.session()

        self.assertEqual(self.texts(session), [])
        self.assertEqual(session["waiting"], 1)

    @override_settings(REVIEW_SESSION_SIZE=2)
    def test_one_session_takes_at_most_the_session_size(self):
        for index in range(4):
            reviewed_term(self.user, f"term {index}", self.course)

        session = self.session()

        self.assertEqual(session["due"], 4)
        self.assertEqual(len(session["rounds"]), 2)

    def test_next_due_at_tells_when_the_next_review_comes(self):
        soon = reviewed_term(self.user, "soon", self.course, overdue_days=-3)
        reviewed_term(self.user, "later", self.course, overdue_days=-9)

        session = self.session()

        self.assertEqual(session["next_due_at"], api_datetime(soon.due_at))

    def test_without_course_is_empty_and_creates_nothing(self):
        self.client.force_authenticate(make_user("bia@example.com"))

        session = self.session()

        self.assertEqual(session["rounds"], [])
        self.assertEqual(session["due"], 0)
        self.assertFalse(Course.objects.filter(user__email="bia@example.com").exists())

    def test_without_known_kinds_there_are_no_rounds(self):
        reviewed_term(self.user, "awkward", self.course)

        session = self.session("?kinds=crossword")

        self.assertEqual((session["due"], session["rounds"]), (1, []))

    def test_without_kinds_every_known_kind_is_allowed(self):
        reviewed_term(self.user, "awkward", self.course)

        self.assertEqual(self.session("")["rounds"][0]["kind"], "listen_write")

    def test_reply_needs_four_read_terms(self):
        for index in range(3):
            reviewed_term(self.user, f"term {index}", self.course)
        make_term(self.user, "never read", course=self.course)

        session = self.session("?kinds=listen_write&kinds=reply")

        self.assertEqual(session["kinds"], ["listen_write"])
        self.assertEqual({r["kind"] for r in session["rounds"]}, {"listen_write"})

    def test_reply_stays_out_of_new_terms_and_retests(self):
        for index in range(3):
            reviewed_term(self.user, f"read {index}", self.course, overdue_days=-5)
        first_review_term(self.user, "first", self.course)
        reviewed_term(self.user, "short", self.course, interval_days=3.0)
        retest = reviewed_term(self.user, "retest", self.course, overdue_days=0.1)
        attempted(retest, points=1)

        session = self.session("?kinds=reply&kinds=listen_write")

        self.assertEqual(set(session["kinds"]), {"reply", "listen_write"})
        self.assertEqual(self.texts(session), ["retest", "short", "first"])
        self.assertEqual({r["kind"] for r in session["rounds"]}, {"listen_write"})

    def test_a_term_with_no_kind_that_fits_has_no_round(self):
        for index in range(3):
            reviewed_term(self.user, f"read {index}", self.course, overdue_days=-5)
        first_review_term(self.user, "first", self.course)

        session = self.session("?kinds=reply")

        self.assertEqual((session["due"], session["rounds"]), (1, []))

    def test_rounds_of_the_same_kind_stay_together(self):
        Course.objects.filter(pk=self.course.pk).update(
            review_capacity=10, daily_limit=10, last_active_on=local_today()
        )
        for index in range(10):
            reviewed_term(self.user, f"term {index}", self.course)

        kinds = [r["kind"] for r in self.session("?kinds=reply&kinds=listen_write")["rounds"]]

        changes = sum(1 for before, after in pairwise(kinds) if before != after)
        self.assertEqual(len(kinds), 10)
        self.assertLessEqual(changes, 1)

    def test_date_too_far_from_the_server_is_rejected(self):
        far = local_today() + timedelta(days=5)

        response = self.client.get(f"/api/v1/reviews?date={far}")

        self.assertEqual(response.status_code, 400)
        self.assertIn("date", response.json())

    def test_invalid_offset_is_rejected(self):
        response = self.client.get("/api/v1/reviews?offset=9000")

        self.assertEqual(response.status_code, 400)
        self.assertIn("offset", response.json())


class CapacityTests(APITestCase):
    def setUp(self):
        super().setUp()
        self.user = make_user()
        self.client.force_authenticate(self.user)
        self.course = make_course(self.user)
        self.yesterday = local_today() - timedelta(days=1)

    def open_app(self) -> Course:
        response = self.client.get(f"/api/v1/reviews?date={local_today()}&offset=0")
        self.assertEqual(response.status_code, 200, response.content)
        self.course.refresh_from_db()
        return self.course

    def last_active(self, on, capacity: int = 10) -> None:
        Course.objects.filter(pk=self.course.pk).update(
            last_active_on=on, review_capacity=capacity, daily_limit=capacity
        )

    def test_first_time_keeps_the_start(self):
        course = self.open_app()

        self.assertEqual((course.review_capacity, course.last_active_on), (10, local_today()))

    def test_leaving_a_review_undone_goes_down(self):
        self.last_active(self.yesterday)
        reviewed_term(self.user, "left", self.course, overdue_days=3)

        self.assertEqual(self.open_app().review_capacity, 9)

    def test_finishing_with_terms_waiting_goes_up(self):
        self.last_active(self.yesterday, capacity=5)
        for index in range(5):
            attempted(
                reviewed_term(self.user, f"done {index}", self.course, overdue_days=-5),
                on=self.yesterday,
            )
        reviewed_term(self.user, "waiting", self.course, overdue_days=3)

        self.assertEqual(self.open_app().review_capacity, 7)

    def test_a_term_due_only_today_does_not_count_against_yesterday(self):
        self.last_active(self.yesterday)
        make_term(
            self.user,
            "due now",
            course=self.course,
            first_read_at=days_ago(30),
            last_session_at=days_ago(8),
            scheduled_days=8.0,
            due_at=clock.day_on(local_today(), 0).start + timedelta(seconds=1),
        )

        self.assertEqual(self.open_app().review_capacity, 10)

    def test_days_away_count_only_the_last_day_the_app_was_opened(self):
        self.last_active(local_today() - timedelta(days=20))
        reviewed_term(self.user, "left", self.course, overdue_days=30)

        self.assertEqual(self.open_app().review_capacity, 9)

    def test_opening_twice_on_the_same_day_adjusts_once(self):
        self.last_active(self.yesterday)
        reviewed_term(self.user, "left", self.course, overdue_days=3)

        self.open_app()

        self.assertEqual(self.open_app().review_capacity, 9)

    def test_new_day_drops_the_extra_revisions_asked_yesterday(self):
        Course.objects.filter(pk=self.course.pk).update(
            last_active_on=self.yesterday, review_capacity=10, daily_limit=20
        )

        self.assertEqual(self.open_app().daily_limit, 10)

    def test_asking_for_more_raises_only_todays_limit_and_frees_first_reviews(self):
        self.last_active(local_today())
        for index in range(3):
            first_review_term(self.user, f"first {index}", self.course)
        before = self.client.get("/api/v1/reviews?kinds=listen_write").json()

        response = self.client.post("/api/v1/reviews/more")

        after = self.client.get("/api/v1/reviews?kinds=listen_write").json()
        self.assertEqual(response.status_code, 204)
        self.assertEqual((before["limit"], len(before["rounds"])), (10, 2))
        self.assertEqual((after["limit"], len(after["rounds"])), (20, 3))
        self.course.refresh_from_db()
        self.assertEqual(self.course.review_capacity, 10)


@override_settings(REVIEW_JITTER=0)
class ReviewAttemptTests(APITestCase):
    def setUp(self):
        super().setUp()
        self.user = make_user()
        self.client.force_authenticate(self.user)
        self.course = make_course(self.user)
        self.term = reviewed_term(self.user, "on the fence", self.course, overdue_days=0)
        self.exercise = make_exercise(self.term)

    def attempt(self, **fields):
        data = {
            "term": str(self.term.id),
            "kind": "listen_write",
            "exercise": str(self.exercise.id),
            "outcome": "first",
            **fields,
        }
        return self.client.post("/api/v1/reviews/attempts", data, format="json")

    def test_a_session_moves_the_interval_and_tells_what_happened(self):
        response = self.attempt()

        self.assertEqual(response.status_code, 201)
        self.term.refresh_from_db()
        self.assertAlmostEqual(self.term.interval_days, 20, delta=0.01)
        self.assertAlmostEqual(self.term.scheduled_days, 20, delta=0.01)
        self.assertAlmostEqual(
            (self.term.due_at - timezone.now()).total_seconds() / 86400, 20, delta=0.01
        )
        self.assertAlmostEqual(self.term.ease, 1.03)
        body = response.json()
        self.assertEqual(body["term"]["level"], 3)
        effect = body["effect"]
        self.assertEqual(
            (effect["role"], effect["rating"], effect["level_before"], effect["level"]),
            ("session", "great", 2, 3),
        )
        self.assertEqual(effect["interval_before"], 8)
        self.assertAlmostEqual(effect["points"], 15)
        self.exercise.refresh_from_db()
        self.assertEqual(self.exercise.served_count, 1)

    def test_signals_are_saved(self):
        played_at = timezone.now() - timedelta(minutes=5)

        self.attempt(
            used_slow=True,
            errors=2,
            hints=1,
            audio_replays=3,
            response_ms=9000,
            played_at=played_at.isoformat(),
            local_date=str(local_today()),
        )

        attempt = ReviewAttempt.objects.get()
        self.assertEqual(
            (
                attempt.used_slow,
                attempt.errors,
                attempt.hints,
                attempt.audio_replays,
                attempt.response_ms,
                attempt.played_at,
                attempt.local_date,
            ),
            (True, 2, 1, 3, 9000, played_at, local_today()),
        )

    def reply_exercise(self, mode: str) -> Exercise:
        return Exercise.objects.create(
            term=self.term,
            kind=Exercise.Kind.REPLY,
            variant=0,
            payload={"mode": mode},
            prompt_version="1.0",
            model="m",
        )

    def test_reply_is_worth_reading_except_for_the_audio(self):
        for mode, points in (("use", 10), ("audio", 15)):
            exercise = self.reply_exercise(mode)

            response = self.attempt(kind="reply", exercise=str(exercise.id))

            self.assertAlmostEqual(response.json()["effect"]["points"], points)
            ReviewAttempt.objects.all().delete()
            exercise.delete()

    def test_one_wrong_tap_does_not_bring_the_term_back_the_same_day(self):
        exercise = self.reply_exercise("use")

        response = self.attempt(kind="reply", exercise=str(exercise.id), outcome="slip", errors=1)

        effect = response.json()["effect"]
        self.assertAlmostEqual(effect["points"], 5)
        self.assertEqual(effect["rating"], "fair")
        self.term.refresh_from_db()
        self.assertAlmostEqual(self.term.interval_days, 5.5, delta=0.01)
        self.assertAlmostEqual(
            (self.term.due_at - timezone.now()).total_seconds() / 86400, 5.5, delta=0.01
        )

    def test_slow_voice_takes_points_but_not_ease(self):
        self.attempt(used_slow=True)

        self.term.refresh_from_db()
        self.assertAlmostEqual(ReviewAttempt.objects.get().points, 12)
        self.assertAlmostEqual(self.term.ease, 1.03)

    def test_slow_voice_does_not_punish_the_ease_a_second_time(self):
        self.attempt(used_slow=True, outcome="retry")

        self.term.refresh_from_db()
        self.assertAlmostEqual(ReviewAttempt.objects.get().points, 3.6)
        self.assertAlmostEqual(self.term.ease, 1.0)

    def test_sentence_already_seen_is_worth_less(self):
        self.attempt()
        tomorrow = local_today() + timedelta(days=1)

        response = self.attempt(local_date=str(tomorrow))

        self.assertAlmostEqual(response.json()["effect"]["points"], 12)

    def test_bad_session_comes_back_in_hours_and_follows_the_curve(self):
        response = self.attempt(outcome="missed")

        self.assertEqual(response.json()["effect"]["rating"], "poor")
        self.term.refresh_from_db()
        self.assertAlmostEqual(self.term.interval_days, 2)
        self.assertAlmostEqual(self.term.ease, 0.9)
        self.assertAlmostEqual(
            (self.term.due_at - timezone.now()).total_seconds() / 3600, 4, delta=0.01
        )

    def test_second_attempt_on_the_same_day_after_a_good_session_changes_nothing(self):
        self.attempt()
        self.term.refresh_from_db()
        interval, due_at = self.term.interval_days, self.term.due_at

        response = self.attempt(outcome="missed")

        self.assertEqual(response.json()["effect"]["role"], "extra")
        self.term.refresh_from_db()
        self.assertEqual((self.term.interval_days, self.term.due_at), (interval, due_at))

    def test_retest_keeps_the_interval_and_sends_the_term_to_the_next_day(self):
        self.attempt(outcome="missed")
        self.term.refresh_from_db()
        interval = self.term.interval_days
        self.term.due_at = timezone.now() - timedelta(minutes=1)
        self.term.save(update_fields=["due_at"])

        response = self.attempt(outcome="first")

        self.assertEqual(response.json()["effect"]["role"], "retest")
        self.term.refresh_from_db()
        self.assertEqual(self.term.interval_days, interval)
        self.assertEqual(self.term.scheduled_days, 1)
        self.assertAlmostEqual(
            (self.term.due_at - timezone.now()).total_seconds() / 86400, 1, delta=0.01
        )

    def test_attempt_before_the_retest_hour_has_no_effect(self):
        self.attempt(outcome="missed")
        self.term.refresh_from_db()
        due_at = self.term.due_at

        response = self.attempt()

        self.assertEqual(response.json()["effect"]["role"], "extra")
        self.term.refresh_from_db()
        self.assertEqual(self.term.due_at, due_at)

    def test_only_one_retest_counts_in_a_day(self):
        self.attempt(outcome="missed")
        self.term.due_at = timezone.now() - timedelta(minutes=1)
        self.term.save(update_fields=["due_at"])
        self.attempt(outcome="missed")
        self.term.refresh_from_db()
        self.term.due_at = timezone.now() - timedelta(minutes=1)
        self.term.save(update_fields=["due_at"])

        response = self.attempt()

        self.assertEqual(response.json()["effect"]["role"], "extra")

    def test_review_after_a_retest_earns_the_full_gain_in_one_day(self):
        self.term.scheduled_days = 1
        self.term.last_session_at = days_ago(1)
        self.term.save(update_fields=["scheduled_days", "last_session_at"])

        self.attempt()

        self.term.refresh_from_db()
        self.assertAlmostEqual(self.term.interval_days, 20, delta=0.01)

    def test_old_attempt_arriving_after_a_newer_one_has_no_effect(self):
        self.attempt()
        self.term.refresh_from_db()
        interval = self.term.interval_days

        response = self.attempt(
            played_at=days_ago(0.5).isoformat(),
            local_date=str(local_today() - timedelta(days=1)),
        )

        self.assertEqual(response.json()["effect"]["role"], "extra")
        self.term.refresh_from_db()
        self.assertEqual(self.term.interval_days, interval)

    def test_first_review_uses_the_card_points_only_once(self):
        term = first_review_term(self.user, "gap", self.course, read_days_ago=1, study_points=2.0)

        first = self.attempt(term=str(term.id), exercise=None)
        term.refresh_from_db()

        self.assertEqual(first.json()["effect"]["role"], "first_review")
        self.assertAlmostEqual(first.json()["effect"]["points"], 17)
        self.assertEqual(term.study_points, 0)

    def test_first_review_earns_the_full_gain_one_day_after_reading(self):
        term = first_review_term(self.user, "gap", self.course, read_days_ago=1)

        self.attempt(term=str(term.id), exercise=None)

        term.refresh_from_db()
        self.assertAlmostEqual(term.interval_days, 5, delta=0.01)

    def test_mastered_term_loses_the_level_when_it_goes_badly(self):
        self.term.interval_days = 32
        self.term.save(update_fields=["interval_days"])

        response = self.attempt(outcome="missed")

        self.assertEqual(
            (response.json()["effect"]["level_before"], response.json()["term"]["level"]), (5, 2)
        )

    def test_same_attempt_again_does_not_count_twice(self):
        attempt_id = str(uuid.uuid4())

        first = self.attempt(id=attempt_id)
        again = self.attempt(id=attempt_id)

        self.assertEqual(again.status_code, 201)
        self.assertEqual(again.json(), first.json())
        self.assertEqual(ReviewAttempt.objects.count(), 1)
        self.exercise.refresh_from_db()
        self.assertEqual(self.exercise.served_count, 1)

    def test_id_used_on_another_term_returns_409(self):
        attempt_id = str(uuid.uuid4())
        other = make_term(self.user, "awkward", course=self.course)
        self.attempt(id=attempt_id)

        response = self.attempt(id=attempt_id, term=str(other.id), exercise=None)

        self.assertEqual(response.status_code, 409)
        other.refresh_from_db()
        self.assertIsNone(other.last_session_at)

    def test_attempt_without_exercise_or_signals_is_recorded(self):
        response = self.attempt(exercise=None, outcome="retry")

        self.assertEqual(response.status_code, 201)
        attempt = ReviewAttempt.objects.get()
        self.assertIsNone(attempt.exercise)
        self.assertEqual(attempt.local_date, local_today())

    def test_exercise_of_another_term_is_rejected(self):
        other = make_exercise(make_term(self.user, "awkward", course=self.course))

        response = self.attempt(exercise=str(other.id))

        self.assertEqual(response.status_code, 400)
        self.assertIn("exercise", response.json())
        self.term.refresh_from_db()
        self.assertEqual(self.term.interval_days, 8)

    def test_term_of_someone_else_is_not_found(self):
        other = make_term(make_user("bia@example.com"), "on the fence")

        response = self.attempt(term=str(other.id), exercise=None)

        self.assertEqual(response.status_code, 404)

    def test_unknown_fields_and_outcomes_are_rejected(self):
        response = self.attempt(outcome="perfect", score=10)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(set(response.json()), {"outcome", "score"})

    def test_dates_far_from_the_real_one_are_rejected(self):
        future = timezone.now() + timedelta(days=5)

        for fields, key in (
            ({"played_at": future.isoformat()}, "played_at"),
            ({"local_date": str(local_today() + timedelta(days=5))}, "local_date"),
        ):
            response = self.attempt(**fields)

            self.assertEqual(response.status_code, 400)
            self.assertIn(key, response.json())
        self.assertFalse(ReviewAttempt.objects.exists())


class StudyTests(APITestCase):
    def setUp(self):
        super().setUp()
        self.user = make_user()
        self.client.force_authenticate(self.user)
        self.term = make_term(self.user, "gap")

    def study(self, event: str, term=None):
        term = term or self.term
        return self.client.post(f"/api/v1/terms/{term.id}/study", {"event": event}, format="json")

    def test_reading_gives_a_point_and_marks_the_first_review_a_day_later(self):
        response = self.study("read")

        self.assertEqual(response.status_code, 200)
        self.term.refresh_from_db()
        self.assertEqual(self.term.study_points, 1)
        self.assertEqual(self.term.scheduled_days, 1)
        self.assertAlmostEqual(
            (self.term.due_at - timezone.now()).total_seconds() / 86400, 1, delta=0.01
        )
        self.assertEqual(response.json()["term"]["level"], 0)

    def test_each_event_counts_only_once(self):
        self.study("read")
        self.study("read")
        self.study("listened")
        self.study("listened")

        self.term.refresh_from_db()
        self.assertEqual(self.term.study_points, 2)

    def test_listening_alone_does_not_schedule(self):
        self.study("listened")

        self.term.refresh_from_db()
        self.assertIsNone(self.term.due_at)

    def test_reading_a_term_already_reviewed_keeps_its_date(self):
        term = reviewed_term(
            self.user, "old", self.term.course, overdue_days=-3, first_read_at=None
        )
        due_at = term.due_at

        self.study("read", term)

        term.refresh_from_db()
        self.assertEqual(term.due_at, due_at)

    def test_points_alone_do_not_change_the_interval(self):
        self.study("read")

        self.term.refresh_from_db()
        self.assertEqual(self.term.interval_days, 2)

    def test_term_of_someone_else_is_not_found(self):
        other = make_term(make_user("bia@example.com"), "gap")

        self.assertEqual(self.study("read", other).status_code, 404)

    def test_unknown_event_is_rejected(self):
        response = self.study("sung")

        self.assertEqual(response.status_code, 400)
        self.assertIn("event", response.json())


@override_settings(REVIEW_SECONDS_PER_DAY=60, REVIEW_JITTER=0)
class AcceleratedTimeTests(APITestCase):
    def setUp(self):
        super().setUp()
        self.user = make_user()
        self.client.force_authenticate(self.user)
        self.course = make_course(self.user)

    def test_one_day_lasts_a_minute(self):
        term = make_term(self.user, "gap", course=self.course)

        self.client.post(f"/api/v1/terms/{term.id}/study", {"event": "read"}, format="json")

        term.refresh_from_db()
        self.assertAlmostEqual((term.due_at - timezone.now()).total_seconds(), 60, delta=1)

    def test_the_day_comes_from_the_api_and_not_from_the_device(self):
        term = reviewed_term(self.user, "gap", self.course, overdue_days=0)
        data = {
            "term": str(term.id),
            "kind": "listen_write",
            "outcome": "first",
            "local_date": str(local_today()),
        }

        response = self.client.post("/api/v1/reviews/attempts", data, format="json")

        attempt = ReviewAttempt.objects.get()
        self.assertEqual(response.status_code, 201)
        self.assertEqual(attempt.local_date, clock.local_date(attempt.played_at, None))
        self.assertNotEqual(attempt.local_date, local_today())


class ClockTests(SimpleTestCase):
    def test_device_day_ends_at_its_own_midnight(self):
        on = local_today()

        day = clock.day_on(on, -180)

        self.assertEqual(day.start.astimezone(UTC).hour, 3)
        self.assertEqual(day.end - day.start, timedelta(days=1))

    def test_without_the_device_date_uses_utc(self):
        now = timezone.now()

        self.assertEqual(clock.local_date(now, None), now.astimezone(UTC).date())

    @override_settings(REVIEW_SECONDS_PER_DAY=60)
    def test_accelerated_day_contains_its_moment_and_lasts_a_minute(self):
        now = timezone.now()

        day = clock.today(now, None, 0)

        self.assertLessEqual(day.start, now)
        self.assertGreater(day.end, now)
        self.assertEqual((day.end - day.start).total_seconds(), 60)
        self.assertEqual(clock.day_on(day.date, 0), day)
