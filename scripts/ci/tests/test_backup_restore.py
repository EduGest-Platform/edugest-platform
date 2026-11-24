"""Metadata privacy, same-count data corruption and disposable-context regressions."""

import importlib.util
import json
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from pathlib import Path

SPEC = importlib.util.spec_from_file_location("backup_restore", Path(__file__).resolve().parents[1] / "backup_restore.py")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class BackupRestoreTests(unittest.TestCase):
    def test_fingerprints_keep_counts_and_digest_without_raw_record_content(self):
        result = MODULE.fingerprint(b'{"secret":"synthetic-private-marker"}\n')
        self.assertEqual(result["rows"], 1)
        self.assertEqual(len(result["sha256"]), 64)
        self.assertNotIn("synthetic-private-marker", json.dumps(result))
        self.assertEqual(MODULE.fingerprint(b"")["rows"], 0)

    def test_same_count_different_content_does_not_match(self):
        first = MODULE.fingerprint(b'{"id":1,"state":"active"}\n')
        changed = MODULE.fingerprint(b'{"id":1,"state":"withdrawn"}\n')
        self.assertEqual(first["rows"], changed["rows"])
        self.assertNotEqual(first["sha256"], changed["sha256"])

    def test_every_disposable_context_gate_is_required(self):
        env = {"GITHUB_ACTIONS": "true", "GISTAR_BACKUP_PROBE": "disposable-synthetic", "GISTAR_ENVIRONMENT": "local"}
        MODULE.validate_context("a" * 64, env)
        for key in env:
            with self.subTest(key=key), self.assertRaises(ValueError):
                MODULE.validate_context("a" * 64, {**env, key: "invalid"})
        with self.assertRaises(ValueError):
            MODULE.validate_context("not-a-container-id", env)

    def test_cleanup_never_drops_a_database_whose_creation_failed(self):
        env = {"GITHUB_ACTIONS": "true", "GISTAR_BACKUP_PROBE": "disposable-synthetic", "GISTAR_ENVIRONMENT": "local"}
        for fail_on in (1, 2):
            calls, created = [], []

            def fake_command(args, **_kwargs):
                calls.append(args)
                if args[3] == "createdb":
                    created.append(args[-1])
                    if len(created) == fail_on:
                        raise RuntimeError("Synthetic existing database")
                return SimpleNamespace(returncode=0, stdout=b"", stderr=b"")

            with self.subTest(fail_on=fail_on), patch.dict(MODULE.os.environ, env), patch.object(MODULE, "command", fake_command):
                report = MODULE.rehearse("a" * 64)
            self.assertEqual(report["status"], "failed")
            dropped = [args[-1] for args in calls if args[3] == "dropdb"]
            self.assertEqual(dropped, [] if fail_on == 1 else [MODULE.SOURCE])
            self.assertNotIn(MODULE.RESTORED, dropped)

    def test_table_identifier_is_quoted_instead_of_interpolating_sql_syntax(self):
        self.assertEqual(MODULE.quoted_identifier('name";SELECT'), '"name"";SELECT"')


if __name__ == "__main__":
    unittest.main()
