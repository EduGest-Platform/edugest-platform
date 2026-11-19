from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core import audit
from app.core.authz import Principal, Scope
from app.core.db import utcnow
from app.modules.admissions.models import Application
from app.modules.catalog.models import Call, Cohort
from app.modules.requirements.models import CallRequirement, EXCEPTION_RESULTS, RequirementReview, RequirementReviewRevision
from app.modules.requirements.schemas import RequirementReviewWrite

_FIRST_REVIEW = {"met", "not_met", "exception_under_review"}
# Allowed result changes. Saving the same result again only amends the reason.
ALLOWED_TRANSITIONS: dict[str | None, set[str]] = {
    None: _FIRST_REVIEW,
    "pending": _FIRST_REVIEW,
    "met": {"not_met"},
    "not_met": {"met", "exception_under_review"},
    "exception_under_review": {"exception_approved", "not_met"},
    "exception_approved": {"not_met"},
}


def require_access(db: Session, principal: Principal, permission: str, call: Call) -> None:
    """Role + scope check. A teacher's cohort scope applies to the cohorts that the call feeds."""
    cohort_ids = db.scalars(select(Cohort.id).where(Cohort.call_id == call.id)).all()
    scopes = [Scope(program_id=call.program_id, call_id=call.id)]
    scopes += [Scope(program_id=call.program_id, call_id=call.id, cohort_id=cohort_id) for cohort_id in cohort_ids]
    if not any(principal.can(permission, scope) for scope in scopes):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "No tienes permiso sobre este ámbito")


def _conflict(detail: str) -> HTTPException:
    return HTTPException(status.HTTP_409_CONFLICT, detail)


def _check_version(review: RequirementReview | None, expected_version: int | None) -> None:
    if review is None and expected_version is not None:
        raise _conflict("Todavía no existe una revisión: omite expected_version")
    if review is not None and expected_version != review.version:
        raise _conflict("La revisión ha cambiado: vuelve a cargarla antes de modificarla")


def _check_transition(current: str | None, new: str) -> None:
    if new != current and new not in ALLOWED_TRANSITIONS[current]:
        raise _conflict(f"No se puede pasar de {current or 'sin revisar'} a {new}")


def save_review(
    db: Session, actor: Principal, application: Application, call: Call, requirement_ref: str, body: RequirementReviewWrite
) -> tuple[RequirementReview, bool]:
    """Creates or revises a review, its history row and the audit event in one transaction. Never touches the application stage."""
    review = db.scalar(
        select(RequirementReview)
        .where(RequirementReview.application_id == application.id, RequirementReview.requirement_ref == requirement_ref)
        .with_for_update()
    )
    current = review.result if review else None
    # Taking or undoing an exception needs its own permission, separate from the plain met / not met review.
    touches_exception = body.result in EXCEPTION_RESULTS or current in EXCEPTION_RESULTS
    require_access(db, actor, "requirements.exception" if touches_exception else "requirements.review", call)
    definition = db.scalar(select(CallRequirement).where(CallRequirement.call_id == call.id, CallRequirement.ref == requirement_ref))
    if definition is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Requisito no configurado para esta convocatoria")
    if review and review.requirement_definition_id not in (None, definition.id):
        raise _conflict("La revisión pertenece a otra definición del requisito")
    _check_version(review, body.expected_version)
    _check_transition(current, body.result)

    now = utcnow()
    created = review is None
    if review is None:
        review = RequirementReview(application_id=application.id, requirement_ref=requirement_ref, version=1)
        db.add(review)
    else:
        review.version += 1
    review.result, review.reviewer_user_id, review.reviewed_at, review.reason = body.result, actor.user.id, now, body.reason
    review.requirement_definition_id = definition.id
    try:
        db.flush()
    except IntegrityError as e:  # concurrent first review of the same requirement
        db.rollback()
        raise _conflict("La revisión ha cambiado: vuelve a cargarla antes de modificarla") from e
    db.add(
        RequirementReviewRevision(
            review_id=review.id, revision=review.version, result=body.result, reviewer_user_id=actor.user.id, reviewed_at=now, reason=body.reason,
            requirement_definition_id=definition.id,
        )
    )
    action = "requirement_review.created" if created else "requirement_review.revised"
    audit.record(
        db, actor, action, "application", str(application.id),
        codigo=application.codigo, requirement_ref=requirement_ref, result=body.result, from_result=current, revision=review.version,
    )
    db.commit()
    return review, created
