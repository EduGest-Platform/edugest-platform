"""KAN-191 / KAN-67: feedback drafts with mandatory human review. Teachers generate, edit and approve; coders only read approved feedback."""

import uuid

from fastapi import APIRouter, Query
from sqlalchemy import func, select

from app.core.deps import DB, CurrentPrincipal
from app.modules.feedback.schemas import ApproveIn, DraftEdit, FeedbackDraftList, FeedbackDraftOut, FeedbackQueue, FeedbackQueueItem, PublishedFeedback
from app.modules.feedback.service import approve, draft_out, edit, generate, load_draft, published, published_out, versions
from app.modules.identity.models import Person
from app.modules.learning.access import require_cohort
from app.modules.learning.models import Enrollment
from app.modules.submissions.models import Assignment, Submission
from app.modules.submissions.router import _is_own_active_enrollment
from app.modules.submissions.service import load_assignment, load_submission, lock_submission

router = APIRouter(tags=["feedback"])

_ERRORS = {403: {"description": "Sin permiso sobre la cohorte"}, 404: {"description": "No encontrado"}}
_CONFLICT = {409: {"description": "Sin resultados de tests, versión desfasada, entrega cambiada o ya aprobado"}}
REVIEW = "submissions.review"


@router.get("/cohorts/{cohort_id}/feedback-queue", response_model=FeedbackQueue, responses=_ERRORS,
            summary="Entregas de una cohorte para revisión de feedback docente")
def list_feedback_queue(p: CurrentPrincipal, db: DB, cohort_id: str, limit: int = Query(25, ge=1, le=100),
                        offset: int = Query(0, ge=0)) -> FeedbackQueue:
    require_cohort(db, p, REVIEW, cohort_id)
    query = (
        select(Submission, Assignment.title, Person.display_name)
        .join(Assignment, Assignment.id == Submission.assignment_id)
        .join(Enrollment, Enrollment.id == Submission.enrollment_id)
        .join(Person, Person.id == Enrollment.person_id)
        .where(Assignment.cohort_id == cohort_id, Enrollment.cohort_id == cohort_id, Assignment.status == "published")
    )
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = db.execute(query.order_by(Submission.submitted_at.desc(), Submission.id).offset(offset).limit(limit))
    return FeedbackQueue(total=total, items=[
        FeedbackQueueItem(submission_id=submission.id, assignment_title=title, learner_name=name,
                          revision=submission.revision, submitted_at=submission.submitted_at,
                          has_check_results=bool((submission.check_results or {}).get("total")))
        for submission, title, name in rows
    ])


@router.post("/submissions/{submission_id}/feedback-drafts", response_model=FeedbackDraftOut, status_code=201,
             responses={**_ERRORS, **_CONFLICT}, summary="Generar un borrador de feedback con la rúbrica y los tests (sin publicar)")
def post_feedback_draft(submission_id: uuid.UUID, p: CurrentPrincipal, db: DB) -> FeedbackDraftOut:
    submission = lock_submission(db, submission_id)
    assignment = load_assignment(db, submission.assignment_id)
    require_cohort(db, p, REVIEW, assignment.cohort_id)
    return draft_out(generate(db, p, assignment, submission))


@router.get("/submissions/{submission_id}/feedback-drafts", response_model=FeedbackDraftList, responses=_ERRORS,
            summary="Todas las versiones del feedback de una entrega (equipo docente)")
def list_feedback_drafts(submission_id: uuid.UUID, p: CurrentPrincipal, db: DB) -> FeedbackDraftList:
    submission = load_submission(db, submission_id)
    require_cohort(db, p, REVIEW, load_assignment(db, submission.assignment_id).cohort_id)
    return FeedbackDraftList(submission_id=submission.id, current_revision=submission.revision,
                             items=[draft_out(d) for d in versions(db, submission.id)])


@router.put("/feedback-drafts/{draft_id}", response_model=FeedbackDraftOut, status_code=201, responses={**_ERRORS, **_CONFLICT},
            summary="Editar un borrador: crea una versión nueva y conserva la anterior")
def put_feedback_draft(draft_id: uuid.UUID, body: DraftEdit, p: CurrentPrincipal, db: DB) -> FeedbackDraftOut:
    draft = load_draft(db, draft_id)
    submission = lock_submission(db, draft.submission_id)
    require_cohort(db, p, REVIEW, load_assignment(db, submission.assignment_id).cohort_id)
    return draft_out(edit(db, p, draft, body.body, body.expected_version))


@router.post("/feedback-drafts/{draft_id}/approve", response_model=FeedbackDraftOut, responses={**_ERRORS, **_CONFLICT},
             summary="Aprobar y publicar un borrador (solo el equipo docente de la cohorte)")
def post_feedback_approval(draft_id: uuid.UUID, body: ApproveIn, p: CurrentPrincipal, db: DB) -> FeedbackDraftOut:
    draft = load_draft(db, draft_id)
    submission = lock_submission(db, draft.submission_id)
    require_cohort(db, p, REVIEW, load_assignment(db, submission.assignment_id).cohort_id)
    return draft_out(approve(db, p, draft, submission, body.expected_revision))


@router.get("/submissions/{submission_id}/feedback", response_model=PublishedFeedback, responses=_ERRORS,
            summary="Feedback publicado de una entrega: el propio coder o el equipo docente. Nunca borradores")
def get_published_feedback(submission_id: uuid.UUID, p: CurrentPrincipal, db: DB) -> PublishedFeedback:
    submission = load_submission(db, submission_id)
    enrollment = db.get(Enrollment, submission.enrollment_id)
    if not _is_own_active_enrollment(p, enrollment):
        require_cohort(db, p, "submissions.read", load_assignment(db, submission.assignment_id).cohort_id)
    approved = published(db, submission.id)
    return PublishedFeedback(submission_id=submission.id, feedback=published_out(approved) if approved else None)
