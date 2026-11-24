"""Regressions for unreferenced duplicate enrollments and cross-run identity changes."""

import importlib.util
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

SCRIPT = Path(__file__).resolve().parents[1] / "verify-f2.py"
SPEC = importlib.util.spec_from_file_location("f2_verifier", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def fixture():
    application = SimpleNamespace(id="synthetic-application", person_id="synthetic-person", stage="admitida")
    enrollment = SimpleNamespace(id="synthetic-enrollment", application_id=application.id,
                                 person_id=application.person_id, cohort_id="COH-E2E-F2", estado="activa")
    decision = SimpleNamespace(decision="admitida", enrollment_id=enrollment.id, cohort_id=enrollment.cohort_id)
    return application, enrollment, decision


class EnrollmentVerifierTests(unittest.TestCase):
    def test_one_linked_enrollment_has_a_stable_minimal_identity(self):
        application, enrollment, decision = fixture()
        self.assertEqual(MODULE.enrollment_identity(application, [enrollment], [decision]),
                         {"application_id": application.id, "enrollment_id": enrollment.id})

    def test_an_unreferenced_second_enrollment_fails_even_with_one_valid_decision(self):
        application, enrollment, decision = fixture()
        unreferenced = SimpleNamespace(id="synthetic-extra-enrollment", application_id=application.id,
                                       person_id=application.person_id, cohort_id="OTHER", estado="activa")
        with self.assertRaises(ValueError):
            MODULE.enrollment_identity(application, [enrollment, unreferenced], [decision])

    def test_missing_or_mismatched_enrollment_does_not_pass(self):
        application, enrollment, decision = fixture()
        with self.assertRaises(ValueError):
            MODULE.enrollment_identity(application, [], [decision])
        for field in ("person_id", "cohort_id", "application_id"):
            with self.subTest(field=field):
                application, enrollment, decision = fixture()
                setattr(enrollment, field, "synthetic-wrong")
                with self.assertRaises(ValueError):
                    MODULE.enrollment_identity(application, [enrollment], [decision])

    def test_repeat_run_requires_the_original_id_and_does_not_overwrite_it(self):
        current = {"application_id": "synthetic-application", "enrollment_id": "synthetic-enrollment"}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "baseline.json"
            MODULE.preserve_identity(current, path)
            original = path.read_bytes()
            MODULE.preserve_identity(current, path)
            with self.assertRaises(ValueError):
                MODULE.preserve_identity({**current, "enrollment_id": "synthetic-changed"}, path)
            self.assertEqual(path.read_bytes(), original)


if __name__ == "__main__":
    unittest.main()
