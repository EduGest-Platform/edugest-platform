"""Create one synthetic support alert in the disposable registration stack."""
import os
from datetime import date

from sqlalchemy import select

from app import models  # noqa: F401
from app.core.db import SessionLocal
from app.modules.learning.models import Enrollment
from app.modules.risk.models import RiskAlert

if os.environ.get("GISTAR_E2E_FIXTURE") != "disposable-synthetic":
    raise RuntimeError("Refusing to modify a non-disposable environment")

with SessionLocal() as db:
    enrollment_id = db.scalar(select(Enrollment.id).where(Enrollment.cohort_id == "COH-IA").order_by(Enrollment.id))
    if not enrollment_id:
        raise RuntimeError("Synthetic cohort must be seeded")
    if db.scalar(select(RiskAlert.id).where(RiskAlert.model_version == "synthetic-browser-review")):
        raise RuntimeError("Use a fresh disposable database for the risk browser fixture")
    db.add(RiskAlert(enrollment_id=enrollment_id, model_version="synthetic-browser-review",
                     model_hash="b" * 64, cutoff=date(2026, 11, 24), status="abstained",
                     abstention_reason="insufficient_exposure"))
    db.commit()
