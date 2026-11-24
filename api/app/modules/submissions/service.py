"""Submission rules (KAN-56). The derived delivery state is a pure function so the assistant tools reuse it."""

from datetime import datetime, timezone

from fastapi import status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core import audit
from app.core.authz import Principal
from app.core.db import utcnow
from app.core.errors import UserFacingError
from app.modules.catalog.models import Cohort
from app.modules.learning.models import Enrollment
from app.modules.submissions.models import Assignment, Submission
from app.modules.submissions.schemas import AssignmentWrite, CheckResults, SubmissionOut, SubmissionWrite


def _after(instant: datetime, deadline: datetime) -> bool:
    """Compare elapsed instants, not local wall times in a repeated DST hour."""
    if instant.utcoffset() is None or deadline.utcoffset() is None:
        raise ValueError("Delivery deadlines require timezone-aware instants")
    return instant.astimezone(timezone.utc) > deadline.astimezone(timezone.utc)


def delivery_state(assignment: Assignment, submission: Submission | None, now: datetime) -> str:
    """on_time / late when delivered; pending / overdue when not. Same four states as the web (domain.ts)."""
    if submission is None:
        return "overdue" if _after(now, assignment.due_at) else "pending"
    return "late" if _after(submission.first_submitted_at, assignment.due_at) else "on_time"


def submission_out(submission: Submission, assignment: Assignment) -> SubmissionOut:
    return SubmissionOut(
        id=submission.id, assignment_id=submission.assignment_id, enrollment_id=submission.enrollment_id,
        portfolio_url=submission.portfolio_url,
        check_results=CheckResults(**submission.check_results) if submission.check_results else None,
        status=submission.status, revision=submission.revision, first_submitted_at=submission.first_submitted_at, submitted_at=submission.submitted_at,
        late=_after(submission.first_submitted_at, assignment.due_at), reviewed_at=submission.reviewed_at,
    )


def create_assignment(db: Session, p: Principal, cohort: Cohort, body: AssignmentWrite) -> Assignment:
    assignment = Assignment(
        cohort_id=cohort.id, title=body.title, description=body.description, due_at=body.due_at,
        rubric=body.rubric, status=body.status, created_by=p.user.id,
    )
    db.add(assignment)
    db.flush()
    audit.record(db, p, "assignment.create", "assignment", str(assignment.id), cohort_id=cohort.id)
    db.commit()
    return assignment


def published_assignments(db: Session, cohort_id: str) -> list[Assignment]:
    query = select(Assignment).where(Assignment.cohort_id == cohort_id, Assignment.status == "published")
    return list(db.scalars(query.order_by(Assignment.due_at, Assignment.id)))


def load_assignment(db: Session, assignment_id) -> Assignment:
    assignment = db.get(Assignment, assignment_id)
    if not assignment:
        raise UserFacingError(status.HTTP_404_NOT_FOUND, "assignment_not_found", "No encontramos esta actividad. Vuelve a la lista de entregas.")
    return assignment


def load_submission(db: Session, submission_id) -> Submission:
    submission = db.get(Submission, submission_id)
    if not submission:
        raise UserFacingError(status.HTTP_404_NOT_FOUND, "submission_not_found", "No encontramos esta entrega.")
    return submission


def save_submission(db: Session, p: Principal, assignment: Assignment, enrollment: Enrollment, body: SubmissionWrite) -> Submission:
    """First delivery or resubmission. A reviewed submission is closed; resubmitting keeps the first date."""
    if enrollment.cohort_id != assignment.cohort_id:
        raise UserFacingError(status.HTTP_409_CONFLICT, "enrollment_other_cohort", "Esta matrícula no pertenece a la cohorte de la actividad.")
    if assignment.status != "published":
        raise UserFacingError(status.HTTP_409_CONFLICT, "assignment_not_published", "La actividad aún no está publicada.")
    query = select(Submission).where(Submission.assignment_id == assignment.id, Submission.enrollment_id == enrollment.id).with_for_update()
    submission = db.scalar(query)
    now = utcnow()
    checks = body.check_results.model_dump() if body.check_results else None
    if submission is None:
        submission = Submission(
            assignment_id=assignment.id, enrollment_id=enrollment.id, portfolio_url=body.portfolio_url, check_results=checks,
            status="submitted", first_submitted_at=now, submitted_at=now, recorded_by=p.user.id,
        )
        db.add(submission)
        action = "submission.create"
    else:
        if submission.status == "reviewed":
            raise UserFacingError(status.HTTP_409_CONFLICT, "submission_reviewed", "Esta entrega ya está revisada y no admite reentregas.")
        artifact_changed = body.portfolio_url != submission.portfolio_url
        submission.portfolio_url = body.portfolio_url
        submission.check_results = next_check_results(submission.check_results, checks, artifact_changed)
        submission.revision += 1
        submission.submitted_at, submission.recorded_by = now, p.user.id
        action = "submission.resubmit"
    try:
        db.flush()
    except IntegrityError:  # a concurrent first delivery won the unique slot
        db.rollback()
        raise UserFacingError(status.HTTP_409_CONFLICT, "submission_duplicate", "Ya existe una entrega para esta actividad. Recarga la página.")
    audit.record(db, p, action, "submission", str(submission.id), assignment_id=str(assignment.id), revision=submission.revision)
    db.commit()
    return submission


def next_check_results(current: dict | None, supplied: dict | None, artifact_changed: bool) -> dict | None:
    """Results always describe the current artifact: fresh ones win; old ones survive only if the artifact is the same."""
    if supplied is not None:
        return supplied
    return None if artifact_changed else current


def lock_submission(db: Session, submission_id) -> Submission:
    """Loads the row FOR UPDATE, so review and resubmission of the same submission are serialized."""
    submission = db.scalar(select(Submission).where(Submission.id == submission_id).with_for_update())
    if not submission:
        raise UserFacingError(status.HTTP_404_NOT_FOUND, "submission_not_found", "No encontramos esta entrega.")
    return submission


def review_submission(db: Session, p: Principal, submission: Submission, expected_revision: int) -> Submission:
    """Marks as reviewed the exact revision the teacher saw. Call with a row from lock_submission."""
    if submission.status == "reviewed":
        raise UserFacingError(status.HTTP_409_CONFLICT, "submission_reviewed", "Esta entrega ya está revisada.")
    if submission.revision != expected_revision:
        raise UserFacingError(status.HTTP_409_CONFLICT, "stale_review",
                              "La persona ha vuelto a entregar mientras la revisabas. Recarga la entrega y revisa la versión nueva.")
    submission.status, submission.reviewed_by, submission.reviewed_at = "reviewed", p.user.id, utcnow()
    audit.record(db, p, "submission.review", "submission", str(submission.id), revision=submission.revision)
    db.commit()
    return submission
