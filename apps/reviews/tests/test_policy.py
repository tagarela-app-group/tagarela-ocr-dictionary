import random

from django.test import SimpleTestCase, override_settings

from apps.exercises.kinds import Effort
from apps.reviews import policy
from apps.vocabulary.models import Term


def play(effort=Effort.LISTEN, outcome="first", seen=False, slow=False, study=0.0) -> policy.Play:
    return policy.Play(
        effort=effort, outcome=outcome, seen_sentence=seen, used_slow=slow, study_points=study
    )


class ScoreTests(SimpleTestCase):
    def test_each_signal_changes_the_points_as_the_table_says(self):
        for expected, signals in (
            (15, play()),
            (12, play(slow=True)),
            (10, play(effort=Effort.READ)),
            (20, play(effort=Effort.PRODUCE)),
            (8, play(effort=Effort.READ, seen=True)),
            (7.5, play(outcome="hint")),
            (4.5, play(outcome="retry")),
            (3, play(effort=Effort.READ, outcome="retry")),
            (0, play(outcome="missed")),
        ):
            self.assertAlmostEqual(policy.score(signals).points, expected)

    def test_card_points_are_added_after_the_multipliers(self):
        self.assertAlmostEqual(policy.score(play(outcome="missed", study=2)).points, 2)
        self.assertAlmostEqual(policy.score(play(slow=True, study=2)).points, 14)

    def test_points_without_support_ignore_only_the_slow_voice(self):
        result = policy.score(play(slow=True, study=1))

        self.assertAlmostEqual(result.points_without_support, 16)


class IntervalTests(SimpleTestCase):
    def test_examples_of_the_proposal_with_an_eight_day_interval(self):
        for days, points, elapsed in (
            (32, 15, 16),
            (20, 15, 8),
            (18, 12, 8),
            (16, 10, 8),
            (11, 15, 2),
            (10, 8, 8),
            (9, 7.5, 8),
            (5, 4.5, 8),
        ):
            time = policy.time_factor(elapsed, 8)
            self.assertEqual(round(policy.new_interval(8, points, 1, time)), days, points)

    def test_good_in_a_row_doubles_from_the_start(self):
        interval = 2.0
        sequence = []
        for _ in range(4):
            interval = policy.new_interval(interval, 10, 1, 1)
            sequence.append(interval)

        self.assertEqual(sequence, [4, 8, 16, 32])

    def test_growth_is_proportional_between_two_points_and_stops_at_the_ends(self):
        self.assertAlmostEqual(policy.growth(2), 0.375)
        self.assertAlmostEqual(policy.growth(12.5), 2.25)
        self.assertEqual(policy.growth(0), 0.25)
        self.assertEqual(policy.growth(40), 3)

    def test_interval_stays_between_one_and_180_days(self):
        self.assertEqual(policy.new_interval(1.5, 0, 1, 1), 1)
        self.assertEqual(policy.new_interval(150, 20, 1, 1), 180)

    def test_a_single_session_never_grows_more_than_four_times(self):
        self.assertEqual(policy.new_interval(10, 20, 1.25, 2), 40)

    def test_time_factor_stays_inside_its_limits(self):
        self.assertEqual(policy.time_factor(0, 8), 0.25)
        self.assertEqual(policy.time_factor(100, 8), 2)
        self.assertEqual(policy.time_factor(1, 1), 1)

    def test_bad_session_comes_back_in_hours_depending_on_the_points(self):
        rng = random.Random(1)

        self.assertAlmostEqual(policy.wait_days(8, 3, rng), 10 / 24)
        self.assertAlmostEqual(policy.wait_days(8, 0, rng), 4 / 24)

    def test_good_session_varies_at_most_ten_percent(self):
        rng = random.Random(1)
        waits = [policy.wait_days(100, 15, rng) for _ in range(50)]

        self.assertGreaterEqual(min(waits), 90)
        self.assertLessEqual(max(waits), 110)
        self.assertGreater(len(set(waits)), 1)


class EaseTests(SimpleTestCase):
    def test_bad_session_takes_away_and_good_one_adds(self):
        self.assertAlmostEqual(policy.next_ease(1, 3.9), 0.9)
        self.assertAlmostEqual(policy.next_ease(1, 8), 1.03)
        self.assertAlmostEqual(policy.next_ease(1, 6), 1)

    def test_stays_between_its_limits(self):
        self.assertEqual(policy.next_ease(0.76, 0), 0.75)
        self.assertEqual(policy.next_ease(1.24, 20), 1.25)


class RatingTests(SimpleTestCase):
    def test_labels_follow_the_points(self):
        for points, label in (
            (3.9, "poor"),
            (4, "fair"),
            (7.9, "fair"),
            (8, "good"),
            (14.9, "good"),
            (15, "great"),
        ):
            self.assertEqual(policy.rating(points), label)


class LevelTests(SimpleTestCase):
    def test_level_follows_the_interval(self):
        for interval, level in (
            (3.9, 0),
            (4, 1),
            (7.9, 1),
            (8, 2),
            (16, 3),
            (24, 4),
            (29.9, 4),
            (30, 5),
            (180, 5),
        ):
            self.assertEqual(Term(interval_days=interval).level, level)


class CapacityTests(SimpleTestCase):
    def test_first_review_slots_stay_between_one_and_a_quarter_of_the_capacity(self):
        self.assertEqual(policy.first_review_slots(10, 0), 2)
        self.assertEqual(policy.first_review_slots(10, 9), 1)
        self.assertEqual(policy.first_review_slots(10, 30), 1)
        self.assertEqual(policy.first_review_slots(25, 0), 6)

    def test_left_something_undone_goes_down(self):
        self.assertEqual(policy.capacity_after(10, left=1, done=3, waiting=9), 9)

    def test_finished_everything_with_terms_waiting_goes_up(self):
        self.assertEqual(policy.capacity_after(10, left=0, done=10, waiting=1), 12)

    def test_finished_with_nothing_waiting_or_did_nothing_stays(self):
        self.assertEqual(policy.capacity_after(10, left=0, done=4, waiting=0), 10)
        self.assertEqual(policy.capacity_after(10, left=0, done=0, waiting=5), 10)

    @override_settings(REVIEW_CAPACITY_MIN=5, REVIEW_CAPACITY_MAX=25)
    def test_stays_between_its_limits(self):
        self.assertEqual(policy.capacity_after(5, left=1, done=0, waiting=0), 5)
        self.assertEqual(policy.capacity_after(25, left=0, done=25, waiting=1), 25)
