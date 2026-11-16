"""Run from repository root: python -m unittest discover -s evals/automation -v."""

import sys
import unittest
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "api"))

from app.modules.automation.engine import Policy, Task, TaskKind, propose
from metrics import Occurrence, evaluate


class RuleTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 11, 16, tzinfo=timezone.utc)
        self.policy = Policy("synthetic-call", "v1", enabled=True)
        self.task = Task("synthetic-call", "synthetic-001", "task-1", TaskKind.INTERVIEW, self.now)

    def test_disabled_by_default(self):
        self.assertEqual(propose([self.task], Policy("synthetic-call", "v1"), self.now), ())

    def test_all_reminders_are_simulated(self):
        for kind in (TaskKind.INTERVIEW, TaskKind.DOCUMENTATION, TaskKind.EXERCISES, TaskKind.INFORMATION_SESSION):
            with self.subTest(kind=kind):
                result = propose([replace(self.task, kind=kind)], self.policy, self.now)
                self.assertEqual(result[0].action, "simulated_reminder")

    def test_completed_and_future_tasks_do_not_trigger(self):
        for task in (replace(self.task, completed=True), replace(self.task, due_at=self.now + timedelta(seconds=1))):
            self.assertEqual(propose([task], self.policy, self.now), ())

    def test_reminder_delay_boundary(self):
        policy = replace(self.policy, reminder_delay=timedelta(hours=1))
        self.assertEqual(propose([self.task], policy, self.now), ())
        self.assertEqual(len(propose([self.task], policy, self.now + timedelta(hours=1))), 1)

    def test_missing_requirements_only_propose_review(self):
        task = replace(self.task, kind=TaskKind.REQUIREMENTS, missing_requirements=("synthetic-document",))
        result = propose([task], self.policy, self.now)
        self.assertEqual(result[0].action, "human_review")
        self.assertEqual(task.missing_requirements, ("synthetic-document",))
        self.assertEqual(propose([replace(task, missing_requirements=())], self.policy, self.now), ())

    def test_silence_grace_boundary_requires_human_review(self):
        task = replace(self.task, kind=TaskKind.RESPONSE)
        self.assertEqual(propose([task], self.policy, self.now + timedelta(days=7, seconds=-1)), ())
        result = propose([task], self.policy, self.now + timedelta(days=7))
        self.assertEqual(result[0].action, "human_review")

    def test_retry_key_is_stable_across_runs(self):
        first = propose([self.task], self.policy, self.now)[0]
        retry = propose([self.task], self.policy, self.now + timedelta(days=1))[0]
        self.assertEqual(first.key, retry.key)

    def test_cross_call_scope_is_rejected_even_when_disabled(self):
        with self.assertRaises(ValueError):
            propose([self.task], Policy("other-call", "v1"), self.now)

    def test_duplicates_are_rejected(self):
        with self.assertRaises(ValueError):
            propose([self.task, self.task], self.policy, self.now)

    def test_invalid_inputs_fail_closed(self):
        for changes in ({"kind": "admit"}, {"task_id": " "}, {"due_at": self.now.replace(tzinfo=None)}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                replace(self.task, **changes)
        with self.assertRaises(ValueError):
            replace(self.policy, response_grace=timedelta(seconds=-1))
        with self.assertRaises(ValueError):
            propose([self.task], self.policy, self.now.replace(tzinfo=None))


class CoverageTests(unittest.TestCase):
    def test_frequencies_are_counted_per_occurrence_not_per_task_type(self):
        rows = [Occurrence(f"synthetic-{i}", "requirements", True, True, f"run-{i}") for i in range(100)]
        rows += [Occurrence(f"synthetic-{i}", "reminder", True, False) for i in range(50)]
        rows += [Occurrence("synthetic-0", "human-interview", False, False)]
        report = evaluate(rows)
        self.assertEqual(report["numerator"], 100)
        self.assertEqual(report["denominator"], 150)
        self.assertAlmostEqual(report["percentage"], 100 * 100 / 150)
        self.assertTrue(report["minimum_case_count_met"])
        self.assertFalse(report["formula_approved"])

    def test_zero_denominator_is_unknown_not_success(self):
        self.assertIsNone(evaluate([])["percentage"])

    def test_duplicate_occurrences_cannot_inflate_result(self):
        row = Occurrence("synthetic-1", "task", True, True, "run-1")
        with self.assertRaises(ValueError):
            evaluate([row, row])

    def test_automated_requires_eligible_task_and_evidence(self):
        for row in (Occurrence("s1", "task", True, True), Occurrence("s1", "task", False, True, "run-1")):
            with self.subTest(row=row), self.assertRaises(ValueError):
                evaluate([row])


if __name__ == "__main__":
    unittest.main()
