"""Read-only persisted enrollment checks after each disposable F2 HTTP journey."""

import json
import os
import re
import sys
from pathlib import Path


def enrollment_identity(application, enrollments, decisions):
    if application.stage != "admitida" or len(enrollments) != 1 or len(decisions) != 1:
        raise ValueError("Expected one applied admission and exactly one application enrollment")
    enrollment, decision = enrollments[0], decisions[0]
    if (enrollment.application_id != application.id or enrollment.person_id != application.person_id
            or enrollment.cohort_id != "COH-E2E-F2" or enrollment.estado != "activa"
            or decision.decision != "admitida" or decision.enrollment_id != enrollment.id
            or decision.cohort_id != enrollment.cohort_id):
        raise ValueError("Enrollment and decision identities do not match")
    return {"application_id": str(application.id), "enrollment_id": str(enrollment.id)}


def preserve_identity(current, baseline):
    if baseline.exists():
        if json.loads(baseline.read_text(encoding="utf-8")) != current:
            raise ValueError("Persisted enrollment identity changed between runs")
    else:
        baseline.write_text(json.dumps(current, sort_keys=True) + "\n", encoding="utf-8")


def main():
    # Deferred imports let count/identity regressions run without an API or database.
    from sqlalchemy import select, text

    from app.core.config import settings
    from app.core.db import SessionLocal
    from app.modules.admissions.models import Application
    from app.modules.identity.models import Person
    from app.modules.learning.models import Enrollment
    from app.modules.selection.models import SelectionDecision

    fixture = os.environ.get("E2E_FIXTURE_ID", "local-f2-admission")
    if (settings.environment != "local" or os.environ.get("GISTAR_E2E_FIXTURE") != "disposable-synthetic"
            or not re.fullmatch(r"[a-zA-Z0-9-]{1,48}", fixture)):
        raise ValueError("Disposable local synthetic fixture required")
    with SessionLocal() as db:
        db.execute(text("SET TRANSACTION READ ONLY"))
        applications = list(db.scalars(select(Application).join(Person, Person.id == Application.person_id).where(
            Person.email == f"e2e.{fixture.lower()}@example.test", Application.call_id == "CONV-IA-2027A",
        )))
        if len(applications) != 1:
            raise ValueError("Expected exactly one fixture application")
        application = applications[0]
        # Query every enrollment for this application, including ones no decision references.
        enrollments = list(db.scalars(select(Enrollment).where(Enrollment.application_id == application.id)))
        decisions = list(db.scalars(select(SelectionDecision).where(SelectionDecision.application_id == application.id)))
        current = enrollment_identity(application, enrollments, decisions)
    # Only technical IDs are stored in the disposable container, never in PostgreSQL or logs.
    preserve_identity(current, Path(f"/tmp/f2-enrollment-{fixture.lower()}.json"))
    print("PASS · F2 exactly one persisted enrollment with stable identity")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        # Do not echo SQL/connection errors, raw records or fixture identity values.
        print("FAIL · F2 persisted enrollment uniqueness or identity", file=sys.stderr)
        raise SystemExit(1) from None
