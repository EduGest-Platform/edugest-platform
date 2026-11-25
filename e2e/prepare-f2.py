"""Create reference data only for the disposable local F2 HTTP journey."""

import os
from datetime import date

from app.core.config import settings
from app.core.db import SessionLocal
from app.modules.catalog.models import Call, Cohort
from app.modules.identity.models import RoleAssignment, User
from sqlalchemy import select

COHORT_START = date(2026, 1, 1)


def main() -> None:
    if settings.environment != "local" or os.environ.get("GISTAR_E2E_FIXTURE") != "disposable-synthetic":
        raise RuntimeError("Disposable local synthetic fixture marker required")
    with SessionLocal() as db:
        call = db.get(Call, "CONV-IA-2027A")
        if call is None or call.program_id != "P-IA":
            raise RuntimeError("Expected synthetic call is unavailable")
        cohort = db.get(Cohort, "COH-E2E-F2")
        if cohort is None:
            db.add(Cohort(id="COH-E2E-F2", program_id="P-IA", call_id=call.id,
                          nombre="Synthetic F2 cohort", inicio=COHORT_START, fin=date(2027, 9, 30)))
        elif (cohort.program_id, cohort.call_id) != ("P-IA", call.id):
            raise RuntimeError("Existing fixture cohort has incompatible scope")
        elif not cohort.inicio <= COHORT_START <= cohort.fin:
            raise RuntimeError("Existing F2 fixture predates the attendance scenario; use a fresh disposable database")

        teacher = db.scalar(select(User).where(User.email == "docente@gistar.example"))
        if teacher is None:
            raise RuntimeError("Expected synthetic teacher is unavailable")
        assignment = db.scalar(select(RoleAssignment).where(
            RoleAssignment.user_id == teacher.id, RoleAssignment.role == "docente",
            RoleAssignment.scope_type == "cohort", RoleAssignment.scope_id == "COH-E2E-F2",
        ))
        if assignment is None:
            db.add(RoleAssignment(user_id=teacher.id, role="docente", scope_type="cohort", scope_id="COH-E2E-F2"))
        elif assignment.revoked_at is not None:
            raise RuntimeError("The synthetic F2 teaching assignment has been revoked")
        db.commit()
    print("F2 synthetic reference cohort and scoped teacher ready")


if __name__ == "__main__":
    main()
