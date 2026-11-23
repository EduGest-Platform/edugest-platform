import uuid

from fastapi import APIRouter, Path, status
from sqlalchemy import select

from app.core.db import utcnow
from app.core.deps import DB, CurrentPrincipal
from app.core.errors import UserFacingError
from app.modules.learning.access import require_cohort, require_enrollment
from app.modules.learning.models import Enrollment
from app.modules.submissions.models import Assignment, Submission
from app.modules.submissions.schemas import (
    AssignmentList,
    AssignmentOut,
    AssignmentWrite,
    EnrollmentDelivery,
    EnrollmentSubmissions,
    SubmissionOut,
    SubmissionWrite,
)
from app.modules.submissions.service import (
    create_assignment,
    delivery_state,
    load_assignment,
    load_submission,
    published_assignments,
    review_submission,
    save_submission,
    submission_out,
)

router = APIRouter(tags=["submissions"])

CohortId = Path(max_length=20)
_ERRORS = {403: {"description": "Sin permiso sobre la cohorte"}, 404: {"description": "No encontrado"}}
_CONFLICT = {409: {"description": "Matrícula de otra cohorte, actividad sin publicar o entrega ya revisada"}}


def _assignment_out(a: Assignment) -> AssignmentOut:
    return AssignmentOut(id=a.id, cohort_id=a.cohort_id, title=a.title, description=a.description, due_at=a.due_at, rubric=list(a.rubric or []), status=a.status)


@router.post("/cohorts/{cohort_id}/assignments", response_model=AssignmentOut, status_code=201, responses=_ERRORS,
             summary="Crear una actividad con plazo en una cohorte")
def post_assignment(body: AssignmentWrite, p: CurrentPrincipal, db: DB, cohort_id: str = CohortId) -> AssignmentOut:
    cohort = require_cohort(db, p, "submissions.review", cohort_id)
    return _assignment_out(create_assignment(db, p, cohort, body))


@router.get("/cohorts/{cohort_id}/assignments", response_model=AssignmentList, responses=_ERRORS,
            summary="Actividades publicadas de una cohorte")
def list_assignments(p: CurrentPrincipal, db: DB, cohort_id: str = CohortId) -> AssignmentList:
    cohort = require_cohort(db, p, "submissions.read", cohort_id)
    return AssignmentList(cohort_id=cohort.id, timezone=cohort.timezone, items=[_assignment_out(a) for a in published_assignments(db, cohort.id)])


@router.put("/assignments/{assignment_id}/submissions/{enrollment_id}", response_model=SubmissionOut, responses={**_ERRORS, **_CONFLICT},
            summary="Registrar o reentregar la entrega de una persona (hasta que se revise)")
def put_submission(assignment_id: uuid.UUID, enrollment_id: uuid.UUID, body: SubmissionWrite, p: CurrentPrincipal, db: DB) -> SubmissionOut:
    assignment = load_assignment(db, assignment_id)
    require_cohort(db, p, "submissions.review", assignment.cohort_id)
    enrollment = db.get(Enrollment, enrollment_id)
    if not enrollment:
        raise UserFacingError(status.HTTP_404_NOT_FOUND, "enrollment_not_found", "No encontramos esta matrícula en la cohorte.")
    return submission_out(save_submission(db, p, assignment, enrollment, body), assignment)


@router.post("/submissions/{submission_id}/review", response_model=SubmissionOut, responses={**_ERRORS, **_CONFLICT},
             summary="Marcar una entrega como revisada por el docente")
def post_review(submission_id: uuid.UUID, p: CurrentPrincipal, db: DB) -> SubmissionOut:
    submission = load_submission(db, submission_id)
    assignment = load_assignment(db, submission.assignment_id)
    require_cohort(db, p, "submissions.review", assignment.cohort_id)
    return submission_out(review_submission(db, p, submission), assignment)


@router.get("/enrollments/{enrollment_id}/submissions", response_model=EnrollmentSubmissions, responses=_ERRORS,
            summary="Estado de cada actividad publicada para una matrícula (a tiempo, tarde, pendiente, vencida)")
def list_enrollment_submissions(enrollment_id: uuid.UUID, p: CurrentPrincipal, db: DB) -> EnrollmentSubmissions:
    enrollment, cohort = require_enrollment(db, p, "submissions.read", enrollment_id)
    assignments = published_assignments(db, cohort.id)
    ids = [a.id for a in assignments]
    rows = db.scalars(select(Submission).where(Submission.enrollment_id == enrollment.id, Submission.assignment_id.in_(ids))) if ids else []
    by_assignment = {s.assignment_id: s for s in rows}
    now = utcnow()
    items = []
    for a in assignments:
        s = by_assignment.get(a.id)
        items.append(EnrollmentDelivery(assignment_id=a.id, title=a.title, due_at=a.due_at, state=delivery_state(a, s, now),
                                        reviewed=bool(s and s.status == "reviewed"), submission=submission_out(s, a) if s else None))
    return EnrollmentSubmissions(enrollment_id=enrollment.id, cohort_id=cohort.id, items=items)
