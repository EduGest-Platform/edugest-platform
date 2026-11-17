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
        self.policy = Policy("synthetic-call", "v1", timedelta(days=7), enabled=True)
        self.task = Task("synthetic-call", "synthetic-001", "task-1", TaskKind.INTERVIEW, self.now)

    def test_disabled_by_default(self):
        self.assertEqual(propose([self.task], Policy("synthetic-call", "v1", timedelta(days=7)), self.now), ())

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
            propose([self.task], Policy("other-call", "v1", timedelta(days=7)), self.now)

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

    def test_policy_version_and_missing_requirements_change_operation_key(self):
        first = propose([self.task], self.policy, self.now)[0]
        newer = propose([self.task], replace(self.policy, version="v2"), self.now)[0]
        self.assertNotEqual(first.key, newer.key)
        task = replace(self.task, kind=TaskKind.REQUIREMENTS, missing_requirements=("A",))
        first = propose([task], self.policy, self.now)[0]
        changed = propose([replace(task, missing_requirements=("A", "B"))], self.policy, self.now)[0]
        self.assertNotEqual(first.key, changed.key)
        reordered = propose([replace(task, missing_requirements=("B", "A", "A"))], self.policy, self.now)[0]
        self.assertEqual(changed.key, reordered.key)

    def test_required_grace_and_strict_task_fields(self):
        with self.assertRaises(TypeError):
            Policy("call", "v1")
        for changes in ({"completed": "false"}, {"completed": 0}, {"missing_requirements": "x"}, {"missing_requirements": (" ",)}, {"missing_requirements": (1,)}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                replace(self.task, **changes)
        with self.assertRaises(ValueError):
            replace(self.policy, enabled="true")

    def test_only_followup_reminders_are_supported(self):
        task = replace(self.task, due_at=self.now + timedelta(hours=1))
        self.assertEqual(propose([task], self.policy, self.now), ())
        self.assertEqual(len(propose([task], self.policy, task.due_at)), 1)


class CoverageTests(unittest.TestCase):
    def report(self, rows, minutes=None):
        return evaluate(rows, manual_minutes=minutes if minutes is not None else {"reminder": 5, "requirements": 60}, catalogue_version="test-only-v1")

    def test_minutes_and_frequencies_weight_tasks_differently(self):
        rows = [Occurrence("s1", f"r-{i}", "reminder", True, True, f"e-{i}") for i in range(3)]
        rows += [Occurrence("s1", "q-1", "requirements", True, False)]
        report = self.report(rows)
        self.assertEqual(report["automated_task_count"], 3)
        self.assertEqual(report["eligible_task_count"], 4)
        self.assertEqual(report["baseline_manual_minutes"], 75)
        self.assertEqual(report["estimated_saved_minutes"], 15)
        self.assertEqual(report["percentage"], 20)

    def test_ineligible_cases_cannot_satisfy_minimum(self):
        rows = [Occurrence(f"s{i}", "i", "interview", False, False) for i in range(100)]
        report = self.report(rows + [Occurrence("eligible", "r", "reminder", True, True, "e1")])
        self.assertEqual(report["case_count"], 101)
        self.assertEqual(report["eligible_case_count"], 1)
        self.assertFalse(report["minimum_case_count_met"])
        report = self.report(rows)
        self.assertEqual(report["eligible_case_count"], 0)
        self.assertIsNone(report["percentage"])
        self.assertFalse(report["minimum_case_count_met"])

    def test_100_eligible_cases_satisfy_minimum(self):
        rows = [Occurrence(f"s{i}", "r", "reminder", True, False) for i in range(100)]
        self.assertTrue(self.report(rows)["minimum_case_count_met"])

    def test_evidence_cannot_back_multiple_automated_occurrences(self):
        rows = [Occurrence("s1", f"r{i}", "reminder", True, True, " shared ") for i in range(3)]
        with self.assertRaises(ValueError):
            self.report(rows)

    def test_normalized_identifiers_prevent_duplicate_cases_and_tasks(self):
        rows = [Occurrence("s1", "r1", " reminder ", True, False), Occurrence("s1 ", "r2", "reminder", True, False)]
        self.assertEqual(self.report(rows)["eligible_case_count"], 1)
        with self.assertRaises(ValueError):
            self.report([rows[0], replace(rows[0], application_id=" s1 ", task_id="r1 ")])
        with self.assertRaises(ValueError):
            self.report([Occurrence("s1", "r1", "reminder", True, True, "e1"), Occurrence("s2", "r2", "reminder", True, True, " e1 ")])

    def test_flags_are_strict_booleans(self):
        for flag in (1, 0, "false", None):
            for name in ("eligible", "automated"):
                with self.subTest(flag=flag, name=name), self.assertRaises(ValueError):
                    Occurrence("s1", "r", "reminder", **{**{"eligible": True, "automated": False}, name: flag})

    def test_missing_invalid_and_zero_minutes(self):
        row = Occurrence("s1", "r", "reminder", True, False)
        for value in (-1, float("nan"), float("inf"), True, "5", None):
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.report([row], {"reminder": value})
        with self.assertRaises(ValueError):
            self.report([row], {})
        self.assertIsNone(self.report([row], {"reminder": 0})["percentage"])
        self.assertIsNone(self.report([])["percentage"])

    def test_automated_requires_eligible_task_and_evidence(self):
        for flags in ((True, None), (False, "e1")):
            with self.subTest(flags=flags), self.assertRaises(ValueError):
                Occurrence("s1", "r", "reminder", flags[0], True, flags[1])

    def test_interview_is_not_eligible(self):
        with self.assertRaises(ValueError):
            Occurrence("s1", "i", "interview", True, False)

    def test_invalid_ids_and_catalogue_are_rejected(self):
        for value in (None, 123, " "):
            with self.subTest(value=value), self.assertRaises(ValueError):
                Occurrence(value, "r", "reminder", True, False)
        with self.assertRaises(ValueError):
            self.report([], {"reminder": 5, " reminder ": 10})
        with self.assertRaises(ValueError):
            evaluate([], manual_minutes={}, catalogue_version=" ")


if __name__ == "__main__":
    unittest.main()
