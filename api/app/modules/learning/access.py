"""Shared lookups for academic endpoints: load a cohort or enrollment and check the caller's cohort scope."""

import uuid

from fastapi import status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.authz import Principal, Scope
from app.core.errors import UserFacingError
from app.modules.catalog.models import Cohort
from app.modules.learning.models import Enrollment


def cohort_scope(cohort: Cohort) -> Scope:
    return Scope(program_id=cohort.program_id, call_id=cohort.call_id, cohort_id=cohort.id)


def load_cohort(db: Session, cohort_id: str) -> Cohort:
    cohort = db.get(Cohort, cohort_id)
    if not cohort:
        raise UserFacingError(status.HTTP_404_NOT_FOUND, "cohort_not_found", "No encontramos esta cohorte. Vuelve a la lista de cohortes.")
    return cohort


def require_cohort(db: Session, p: Principal, perm: str, cohort_id: str) -> Cohort:
    """Loads the cohort and returns 403 unless `perm` is granted on it (globally, on its program or on the cohort)."""
    cohort = load_cohort(db, cohort_id)
    p.require(perm, cohort_scope(cohort))
    return cohort


def require_enrollment(db: Session, p: Principal, perm: str, enrollment_id: uuid.UUID) -> tuple[Enrollment, Cohort]:
    enrollment = db.get(Enrollment, enrollment_id)
    if not enrollment:
        raise UserFacingError(status.HTTP_404_NOT_FOUND, "enrollment_not_found", "No encontramos esta matrícula. Vuelve a la cohorte y ábrela de nuevo.")
    return enrollment, require_cohort(db, p, perm, enrollment.cohort_id)


def require_own_active_enrollment(db: Session, p: Principal, enrollment_id: uuid.UUID) -> Enrollment:
    enrollment = None
    if p.user.person_id is not None:
        enrollment = db.scalar(
            select(Enrollment).where(
                Enrollment.id == enrollment_id, Enrollment.person_id == p.user.person_id, Enrollment.estado == "activa"
            )
        )
    if enrollment is None:
        raise UserFacingError(404, "enrollment_not_found", "No encontramos una matrícula activa para tu cuenta.")
    return enrollment
