"""Elapsed-duration deadlines must be invariant under timezone representation."""

import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "api"))

from app.modules.automation.engine import Policy, Task, TaskKind, propose


class DaylightSavingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.madrid = ZoneInfo("Europe/Madrid")

    def assert_boundary(self, kind, due, boundary, **durations):
        policy = Policy("synthetic", "dst-v1", timedelta(0), enabled=True, **durations)
        task = Task("synthetic", "app-1", "task-1", kind, due)
        before = (boundary.astimezone(timezone.utc) - timedelta(microseconds=1)).astimezone(self.madrid)
        self.assertEqual(propose([task], policy, before), ())
        self.assertEqual(len(propose([task], policy, boundary)), 1)
        # Representation, including now/due with different tzinfo objects, cannot change the result.
        utc_task = Task("synthetic", "app-1", "task-1", kind, due.astimezone(timezone.utc))
        self.assertEqual(len(propose([utc_task], policy, boundary)), 1)
        self.assertEqual(len(propose([task], policy, boundary.astimezone(timezone.utc))), 1)

    def test_followup_24_elapsed_hours_across_both_clock_changes(self):
        for month, day, hour in ((3, 28, 13), (10, 24, 11)):
            with self.subTest(month=month):
                due = datetime(2026, month, day, 12, tzinfo=self.madrid)
                boundary = datetime(2026, month, day + 1, hour, tzinfo=self.madrid)
                self.assert_boundary(TaskKind.DOCUMENTATION, due, boundary, reminder_delay=timedelta(hours=24))

    def test_response_grace_is_elapsed_time_across_both_clock_changes(self):
        for month, day, hour in ((3, 28, 13), (10, 24, 11)):
            with self.subTest(month=month):
                due = datetime(2026, month, day, 12, tzinfo=self.madrid)
                boundary = datetime(2026, month, day + 1, hour, tzinfo=self.madrid)
                policy = Policy("synthetic", "dst-v1", timedelta(hours=24), enabled=True)
                task = Task("synthetic", "app-1", "response", TaskKind.RESPONSE, due)
                before = boundary.astimezone(timezone.utc) - timedelta(microseconds=1)
                self.assertEqual(propose([task], policy, before), ())
                self.assertEqual(len(propose([task], policy, boundary)), 1)
                self.assertEqual(len(propose([task], policy, boundary.astimezone(timezone.utc))), 1)

    def test_pre_session_lead_is_elapsed_time_and_stops_at_due(self):
        for month, day, start_hour in ((3, 29, 11), (10, 25, 13)):
            with self.subTest(month=month):
                due = datetime(2026, month, day, 12, tzinfo=self.madrid)
                start = datetime(2026, month, day - 1, start_hour, tzinfo=self.madrid)
                self.assert_boundary(TaskKind.INFORMATION_SESSION, due, start, reminder_lead=timedelta(hours=24))
                policy = Policy("synthetic", "dst-v1", timedelta(0), enabled=True, reminder_lead=timedelta(hours=24))
                task = Task("synthetic", "app-1", "session", TaskKind.INFORMATION_SESSION, due)
                self.assertEqual(propose([task], policy, due), ())

    def test_repeated_hour_respects_fold_for_due_and_now(self):
        # 02:45 CEST (00:45 UTC) is BEFORE 02:30 CET (01:30 UTC).
        due = datetime(2026, 10, 25, 2, 30, tzinfo=self.madrid, fold=1)
        before = datetime(2026, 10, 25, 2, 45, tzinfo=self.madrid, fold=0)
        policy = Policy("synthetic", "dst-v1", timedelta(0), enabled=True, reminder_lead=timedelta(hours=1))
        task = Task("synthetic", "app-1", "session", TaskKind.INFORMATION_SESSION, due)
        self.assertEqual(len(propose([task], policy, before)), 1)
        self.assertEqual(len(propose([task], policy, before.astimezone(timezone.utc))), 1)
        self.assertEqual(propose([task], policy, due), ())
        for kind in (TaskKind.DOCUMENTATION, TaskKind.RESPONSE):
            with self.subTest(kind=kind):
                other = Task("synthetic", "app-1", "followup", kind, due)
                self.assertEqual(propose([other], policy, before), ())
                self.assertEqual(len(propose([other], policy, due)), 1)


if __name__ == "__main__":
    unittest.main()
