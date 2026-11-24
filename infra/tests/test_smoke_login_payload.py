"""Exercise the actual stdin/stdout credential boundary with synthetic values only."""

import json
import subprocess
import sys
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "smoke-login-payload.py"


class LoginPayloadTests(unittest.TestCase):
    def test_special_characters_round_trip_without_stderr_or_argument_interpolation(self):
        for value in ('synthetic-password', 'synthetic-"quote', 'synthetic-\\slash',
                      'synthetic-\nline', 'synthetic-\ttab', 'sintética-contraseña'):
            with self.subTest(kind=repr(value)):
                result = subprocess.run([sys.executable, str(SCRIPT)], input=value.encode("utf-8"),
                                        capture_output=True)
                self.assertEqual(result.returncode, 0)
                self.assertEqual(result.stderr, b"")
                self.assertEqual(json.loads(result.stdout), {"email": "admin@gistar.example", "password": value})

    def test_invalid_encoding_fails_without_echoing_the_input(self):
        result = subprocess.run([sys.executable, str(SCRIPT)], input=b"\xffsynthetic", capture_output=True)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, b"")
        self.assertNotIn(b"synthetic", result.stderr)

    def test_missing_password_fails_without_emitting_a_login_body(self):
        result = subprocess.run([sys.executable, str(SCRIPT)], input="", capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, "")
        self.assertEqual(result.stderr.strip(), "Missing smoke-test password on stdin")


if __name__ == "__main__":
    unittest.main()
