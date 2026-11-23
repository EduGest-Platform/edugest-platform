"""Build a smoke-test login body from stdin; never put credentials in process arguments."""

import json
import sys


def main() -> int:
    try:
        password = sys.stdin.buffer.read().decode("utf-8")
    except UnicodeDecodeError:
        print("Smoke-test password must be UTF-8", file=sys.stderr)
        return 2
    if not password:
        print("Missing smoke-test password on stdin", file=sys.stderr)
        return 2
    json.dump({"email": "admin@gistar.example", "password": password}, sys.stdout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
