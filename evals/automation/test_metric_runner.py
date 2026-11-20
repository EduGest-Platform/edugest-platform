"""KAN-199: scenario integrity, explicit assumptions, deterministic files and CLI failures."""
import copy
import csv
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from metric_examples import scenario
from run_metrics import MAX_INPUT_BYTES, build_report, evaluate_file


class MetricRunnerTests(unittest.TestCase):
    def test_manual_only_and_weighted_mixed_scenarios_do_not_claim_measured_savings(self):
        manual, mixed = build_report(scenario()), build_report(scenario(True))
        self.assertEqual(manual["metric"]["eligible_case_count"], 100)
        self.assertEqual(manual["metric"]["eligible_task_count"], 200)
        self.assertEqual(manual["metric"]["percentage"], 0)
        self.assertEqual(mixed["metric"]["automated_task_count"], 150)
        self.assertEqual(mixed["metric"]["baseline_manual_minutes"], 3000)
        self.assertEqual(mixed["metric"]["estimated_saved_minutes"], 2000)
        self.assertAlmostEqual(mixed["metric"]["percentage"], 200 / 3)
        self.assertFalse(mixed["production_evidence_authenticated"])
        self.assertEqual(mixed["status"], "HYPOTHETICAL_SCENARIO_NOT_MEASURED_SAVINGS")
        self.assertEqual(mixed["metric"]["client_approval"], "PENDING")

    def test_noncompletion_evidence_kinds_are_rejected(self):
        for kind in ("evaluation", "human_review", "simulated_reminder", "delivered", "actual_completion"):
            with self.subTest(kind=kind):
                payload = scenario(True)
                payload["evidence"][0]["kind"] = kind
                with self.assertRaisesRegex(ValueError, "not completion evidence"):
                    build_report(payload)

    def test_evidence_must_bind_to_application_task_and_type(self):
        for key in ("application_id", "task_id", "task_type"):
            payload = scenario(True)
            payload["evidence"][0][key] = "synthetic-other"
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, "must match"):
                build_report(payload)

    def test_missing_duplicate_unused_and_reused_evidence_are_rejected(self):
        payloads = []
        missing = scenario(True)
        missing["evidence"].pop(0)
        payloads.append(missing)
        duplicate = scenario(True)
        duplicate["evidence"].append(copy.deepcopy(duplicate["evidence"][0]))
        payloads.append(duplicate)
        unused = scenario(True)
        unused["occurrences"][0].update(automated=False, evidence_id=None)
        payloads.append(unused)
        reused = scenario(True)
        reused["occurrences"].append(copy.deepcopy(reused["occurrences"][0]))
        payloads.append(reused)
        for payload in payloads:
            with self.subTest(payload_index=payloads.index(payload)), self.assertRaises(ValueError):
                build_report(payload)

    def test_explicit_hypothetical_unit_and_strict_schema_are_required(self):
        mutations = [lambda p: p.update(synthetic_only=False), lambda p: p.update(schema_version=True),
                     lambda p: p.update(extra="unexpected"), lambda p: p["catalogue"].update(unit="per_batch"),
                     lambda p: p["catalogue"].update(approval="approved"),
                     lambda p: p["occurrences"][0].update(automated="false"),
                     lambda p: p["occurrences"][0].update(extra="unexpected")]
        for mutate in mutations:
            payload = scenario()
            mutate(payload)
            with self.assertRaises((ValueError, TypeError)):
                build_report(payload)

    def test_sensitive_or_formula_like_identifiers_are_rejected(self):
        for value in ("person@example.test", "12345678Z", "612345678", "=HYPERLINK(fake)", " synthetic-case-1"):
            payload = scenario()
            payload["occurrences"][0]["application_id"] = value
            with self.subTest(value=value), self.assertRaises(ValueError):
                build_report(payload)

    def test_missing_negative_and_nonfinite_minutes_fail_and_zero_is_undefined(self):
        for minutes in ({}, {"documentation": -1, "exercises": 20}, {"documentation": float("inf"), "exercises": 20}):
            payload = scenario()
            payload["catalogue"]["manual_minutes"] = minutes
            with self.assertRaises(ValueError):
                build_report(payload)
        payload = scenario()
        payload["catalogue"]["manual_minutes"] = {"documentation": 0, "exercises": 0}
        self.assertIsNone(build_report(payload)["metric"]["percentage"])

    def test_interviews_cannot_become_eligible_by_supplying_minutes(self):
        payload = scenario()
        payload["occurrences"][0]["task_type"] = "interview"
        payload["catalogue"]["manual_minutes"]["interview"] = 10
        with self.assertRaises(ValueError):
            build_report(payload)

    def test_json_csv_and_input_are_reproducible_and_undefined_is_explicit(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "input.json"
            payload = scenario()
            payload["catalogue"]["manual_minutes"] = {"documentation": 0, "exercises": 0}
            original = json.dumps(payload, sort_keys=True).encode()
            source.write_bytes(original)
            first = evaluate_file(source, root / "one")
            second = evaluate_file(source, root / "two")
            self.assertEqual(first, second)
            self.assertEqual(source.read_bytes(), original)
            for name in ("report.json", "summary.csv"):
                self.assertEqual((root / "one" / name).read_bytes(), (root / "two" / name).read_bytes())
            with (root / "one" / "summary.csv").open(encoding="utf-8", newline="") as stream:
                row = next(csv.DictReader(stream))
            self.assertEqual(row["percentage"], "undefined")
            self.assertIsNone(json.loads((root / "one" / "report.json").read_text())["metric"]["percentage"])

    def test_duplicate_json_keys_nonfinite_json_and_size_limit_do_not_create_outputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "input.json"
            for raw in ('{"schema_version":1,"schema_version":1}', '{"bad":NaN}', ' ' * (MAX_INPUT_BYTES + 1)):
                source.write_text(raw, encoding="utf-8")
                with self.assertRaises(ValueError):
                    evaluate_file(source, root / "invalid")
                self.assertFalse((root / "invalid").exists())

    def test_cli_returns_nonzero_without_echoing_bad_input(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "input.json"
            source.write_text('{"unexpected":"Synthetic-Private-Canary"}', encoding="utf-8")
            result = subprocess.run([sys.executable, str(Path(__file__).with_name("run_metrics.py")),
                                     "--input", str(source), "--out", str(root / "bad")], capture_output=True, text=True)
            self.assertEqual(result.returncode, 2)
            self.assertNotIn("Synthetic-Private-Canary", result.stdout + result.stderr)
            self.assertFalse((root / "bad").exists())


    def test_generated_inputs_and_reports_use_portable_lf_bytes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = subprocess.run([sys.executable, str(Path(__file__).with_name("metric_examples.py")),
                                     "--out", str(root / "inputs")], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            source = root / "inputs" / "synthetic-mixed-100.json"
            self.assertNotIn(b"\r\n", source.read_bytes())
            evaluate_file(source, root / "report")
            for filename in ("report.json", "summary.csv"):
                self.assertNotIn(b"\r\n", (root / "report" / filename).read_bytes())
