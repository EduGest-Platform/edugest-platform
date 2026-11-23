"""Count evidence, failure propagation and redaction regressions for KAN-219."""

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "summarize_junit.py"
SPEC = importlib.util.spec_from_file_location("junit_summary", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
COMMIT = "a" * 40
SUITE = '<testsuite tests="4" failures="0" errors="0" skipped="1"><testcase name="PRIVATE"><system-out>SECRET</system-out></testcase></testsuite>'


class SummaryTests(unittest.TestCase):
    def summarize(self, text, outcome="success", commit=COMMIT):
        with tempfile.TemporaryDirectory() as directory:
            report = Path(directory) / "input.xml"
            report.write_text(text, encoding="utf-8")
            return MODULE.summarize(report, outcome, commit)

    def test_counts_and_omits_all_test_identity_and_output(self):
        result = self.summarize(f'<testsuites name="PRIVATE">{SUITE}</testsuites>')
        self.assertEqual(result["status"], "passed")
        self.assertEqual(result["counts"], {"tests": 4, "failures": 0, "errors": 0, "skipped": 1, "passed": 3})
        self.assertNotIn("PRIVATE", json.dumps(result))
        self.assertNotIn("SECRET", json.dumps(result))

    def test_aggregates_sibling_suites_without_counting_parent_totals(self):
        result = self.summarize(f'<testsuites tests="8">{SUITE}{SUITE}</testsuites>')
        self.assertEqual(result["counts"]["tests"], 8)
        self.assertEqual(result["counts"]["passed"], 6)

    def test_failure_error_and_process_failure_never_pass(self):
        for field in ("failures", "errors"):
            with self.subTest(field=field):
                self.assertEqual(self.summarize(SUITE.replace(f'{field}="0"', f'{field}="1"'))["status"], "failed")
        for outcome in ("failure", "cancelled", "skipped"):
            with self.subTest(outcome=outcome):
                self.assertEqual(self.summarize(SUITE, outcome)["status"], "failed")

    def test_empty_all_skipped_and_invalid_commit_do_not_claim_success(self):
        for text in (SUITE.replace('tests="4"', 'tests="1"'), '<testsuite tests="0" failures="0" errors="0" skipped="0"/>'):
            self.assertEqual(self.summarize(text)["status"], "failed")
        result = self.summarize(SUITE, commit="PRIVATE")
        self.assertIsNone(result["commit"])
        self.assertEqual(result["status"], "failed")

    def test_malformed_missing_negative_or_inconsistent_counts_are_invalid(self):
        for text in ('<broken', '<testsuite/>', SUITE.replace('tests="4"', 'tests="-1"'), SUITE.replace('tests="4"', 'tests="0"')):
            with self.subTest(text=text):
                result = self.summarize(text)
                self.assertEqual(result["status"], "invalid")
                self.assertIsNone(result["counts"])

    def test_nested_suites_and_unrecognised_roots_are_invalid(self):
        for text in (f'<testsuite tests="4">{SUITE}</testsuite>', '<other/>'):
            self.assertEqual(self.summarize(text)["status"], "invalid")

    def test_missing_report_is_unavailable_with_no_invented_zero_counts(self):
        with tempfile.TemporaryDirectory() as directory:
            result = MODULE.summarize(Path(directory) / "missing.xml", "failure", COMMIT)
        self.assertEqual(result["status"], "unavailable")
        self.assertIsNone(result["counts"])

    def test_cli_writes_only_safe_evidence_and_keeps_failure_exit_status(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            report, output, summary = [folder / name for name in ("input.xml", "output.json", "summary.md")]
            report.write_text(SUITE.replace('failures="0"', 'failures="1"'), encoding="utf-8")
            result = subprocess.run([sys.executable, str(SCRIPT), "--input", str(report), "--output", str(output),
                                     "--summary", str(summary), "--commit", COMMIT, "--outcome", "failure"], capture_output=True, text=True)
            self.assertEqual(result.returncode, 1)
            self.assertEqual(json.loads(output.read_text(encoding="utf-8"))["status"], "failed")
            for text in (output.read_text(encoding="utf-8"), summary.read_text(encoding="utf-8"), result.stdout, result.stderr):
                self.assertNotIn("PRIVATE", text)
                self.assertNotIn("SECRET", text)


if __name__ == "__main__":
    unittest.main()
