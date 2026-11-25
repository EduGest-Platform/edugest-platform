from fastapi import APIRouter
from sqlalchemy import select

from app.core.deps import DB, CurrentPrincipal
from app.modules.catalog.models import Cohort
from app.modules.learning.learner_schemas import LearnerEnrollment, LearnerEnrollments
from app.modules.learning.models import Enrollment

router = APIRouter(prefix="/me/enrollments", tags=["learning"])


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
