"""Create reference data only for the disposable local F2 HTTP journey."""

import os
from datetime import date

from app.core.config import settings
from app.core.db import SessionLocal
from app.modules.catalog.models import Call, Cohort


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
                          nombre="Synthetic F2 cohort", inicio=date(2027, 3, 1), fin=date(2027, 9, 30)))
            db.commit()
        elif (cohort.program_id, cohort.call_id) != ("P-IA", call.id):
            raise RuntimeError("Existing fixture cohort has incompatible scope")
    print("F2 synthetic reference cohort ready")


if __name__ == "__main__":
    main()
