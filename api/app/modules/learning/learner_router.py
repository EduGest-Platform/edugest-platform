import uuid
from datetime import date

from fastapi import APIRouter
from sqlalchemy import select

from app.core.deps import DB, CurrentPrincipal
from app.modules.attendance.queries import records_of, sessions_in
from app.modules.attendance.service import summarize
from app.modules.catalog.models import Cohort
from app.modules.learning.access import load_cohort, require_own_active_enrollment
from app.modules.learning.learner_schemas import LearnerAttendance, LearnerEnrollment, LearnerEnrollments
from app.modules.learning.models import Enrollment

router = APIRouter(prefix="/me/enrollments", tags=["learning"])
OWN_ENROLLMENT_ERRORS = {404: {"description": "No active enrollment for the signed-in person"}}


@router.get("", response_model=LearnerEnrollments, summary="List enrollments for the signed-in person")
def list_own_enrollments(p: CurrentPrincipal, db: DB) -> LearnerEnrollments:
    person_id = p.user.person_id
    if person_id is None:
        return LearnerEnrollments(items=[])

    rows = db.execute(
        select(Enrollment.id, Enrollment.cohort_id, Cohort.nombre, Enrollment.estado)
        .join(Cohort, Cohort.id == Enrollment.cohort_id)
        .where(Enrollment.person_id == person_id)
        .order_by(Enrollment.created_at.desc(), Enrollment.id)
    )
    return LearnerEnrollments(
        items=[
            LearnerEnrollment(enrollment_id=enrollment_id, cohort_id=cohort_id, cohort_name=name, status=state)
            for enrollment_id, cohort_id, name, state in rows
        ]
    )


@router.get(
    "/{enrollment_id}/attendance", response_model=LearnerAttendance, responses=OWN_ENROLLMENT_ERRORS,
    summary="Read attendance totals for the signed-in person's active enrollment",
)
def own_attendance(
    enrollment_id: uuid.UUID, p: CurrentPrincipal, db: DB, date_from: date | None = None, date_to: date | None = None
) -> LearnerAttendance:
    enrollment = require_own_active_enrollment(db, p, enrollment_id)
    cohort = load_cohort(db, enrollment.cohort_id)
    sessions = sessions_in(db, cohort.id, date_from, date_to)
    records = records_of(db, sessions, enrollment_id=enrollment.id)
    totals, = summarize(sessions, records, [enrollment.id], cohort.timezone)
    return LearnerAttendance(
        cohort_id=cohort.id, timezone=cohort.timezone, date_from=date_from, date_to=date_to, totals=totals
    )
