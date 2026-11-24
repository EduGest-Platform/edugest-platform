"""Round-trip a fresh synthetic seed through pg_dump/pg_restore in the CI service only."""

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = "gistar_backup_probe"
RESTORED = "gistar_restore_probe"


def validate_context(container, env):
    if (env.get("GITHUB_ACTIONS") != "true" or env.get("GISTAR_BACKUP_PROBE") != "disposable-synthetic"
            or env.get("GISTAR_ENVIRONMENT") != "local" or not re.fullmatch(r"[a-f0-9]{12,64}", container)):
        raise ValueError("Disposable CI PostgreSQL service required")


def fingerprint(rows):
    return {"rows": len(rows.splitlines()), "sha256": hashlib.sha256(rows).hexdigest()}


def quoted_identifier(name):
    return '"' + name.replace('"', '""') + '"'


def command(args, *, env=None, stdin=None, stdout=None, allow_failure=False):
    result = subprocess.run(args, cwd=ROOT / "api", env=env, stdin=stdin,
                            stdout=stdout if stdout is not None else subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode and not allow_failure:
        # Never echo commands, connection strings, records, captured output or provider errors.
        raise RuntimeError("Synthetic backup rehearsal command failed")
    return result


def psql(container, database, sql, **kwargs):
    return command(["docker", "exec", container, "psql", "-X", "-qAt", "-v", "ON_ERROR_STOP=1",
                    "-U", "gistar", "-d", database, "-c", sql], **kwargs)


def snapshot(container, database):
    tables = psql(container, database, "SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename").stdout
    result = {}
    for table in tables.decode("utf-8").splitlines():
        sql = f"SELECT row_to_json(t)::text FROM public.{quoted_identifier(table)} AS t ORDER BY row_to_json(t)::text"
        result[table] = fingerprint(psql(container, database, sql).stdout)
    return result


def rehearse(container):
    validate_context(container, os.environ)
    created = []
    report = {"schema_version": 1, "synthetic_only": True, "status": "failed", "tables": None,
              "audit_protected": False, "cleanup_succeeded": False}
    try:
        for database in (SOURCE, RESTORED):
            command(["docker", "exec", container, "createdb", "-U", "gistar", database])
            created.append(database)  # Only a database actually created here may be dropped by cleanup.
        env = {**os.environ, "GISTAR_DATABASE_URL": f"postgresql+psycopg://gistar:gistar@localhost:5432/{SOURCE}"}
        command([sys.executable, "-m", "alembic", "upgrade", "head"], env=env)
        command([sys.executable, "-m", "app.seed"], env=env)
        # Add a genuine synthetic login so the restored append-only trigger is exercised on a non-empty audit.
        login = """from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings
with TestClient(app) as client:
    response = client.post('/api/v1/auth/login', json={
        'email': 'admin@gistar.example', 'password': settings.demo_password,
    })
    assert response.status_code == 200
"""
        command([sys.executable, "-c", login], env=env)
        source = snapshot(container, SOURCE)
        if (source.get("application", {}).get("rows", 0) < 100
                or source.get("audit_event", {}).get("rows", 0) < 1):
            raise RuntimeError("Synthetic seed or audit evidence is incomplete")
        with tempfile.TemporaryDirectory(prefix="kan217-") as directory:
            dump = Path(directory) / "synthetic.dump"
            with dump.open("wb") as stream:
                command(["docker", "exec", container, "pg_dump", "-U", "gistar", "-d", SOURCE,
                         "--format=custom", "--no-owner", "--no-acl"], stdout=stream)
            with dump.open("rb") as stream:
                command(["docker", "exec", "-i", container, "pg_restore", "-U", "gistar", "-d", RESTORED,
                         "--exit-on-error", "--no-owner", "--no-acl"], stdin=stream)
            if snapshot(container, RESTORED) != source:
                raise RuntimeError("Restored table fingerprints differ")
            blocked = psql(container, RESTORED, "UPDATE audit_event SET action='synthetic.probe_mutation'", allow_failure=True)
            if blocked.returncode == 0 or b"solo inserci" not in blocked.stderr:
                raise RuntimeError("Restored audit trigger did not reject the update")
            if snapshot(container, RESTORED) != source:
                raise RuntimeError("Rejected audit update changed restored evidence")
        report.update(status="passed", tables=source, audit_protected=True)
    except Exception:
        report["status"] = "failed"
    finally:
        cleanup_ok = True
        for database in reversed(created):
            try:
                command(["docker", "exec", container, "dropdb", "-U", "gistar", database])
            except Exception:
                cleanup_ok = False
        report["cleanup_succeeded"] = cleanup_ok
        if not cleanup_ok:
            report["status"] = "failed"
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--container", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = rehearse(args.container)
    except Exception:
        print("FAIL · disposable CI backup context required", file=sys.stderr)
        return 1
    args.output.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print("PASS · synthetic backup and restore" if result["status"] == "passed" else "FAIL · synthetic backup and restore")
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
