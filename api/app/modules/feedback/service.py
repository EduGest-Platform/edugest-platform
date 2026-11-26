"""KAN-191 / KAN-204: feedback drafts are generated, edited and approved by people; nothing is published on its own.

The template uses only the rubric, the pre-computed test results and the delivery state, never the portfolio URL
or any submitted content. Every action is audited with ids and versions, never with the feedback text.
"""

from datetime import datetime

from fastapi import status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core import audit
from app.core.authz import Principal
from app.core.db import utcnow
from app.core.errors import UserFacingError
from app.modules.feedback.models import FeedbackDraft
from app.modules.feedback.schemas import FeedbackDraftOut, PublishedFeedbackOut
from app.modules.submissions.models import Assignment, Submission
from app.modules.submissions.service import delivery_state

LABELS = {
    ("template", "draft"): "Borrador automático (plantilla con la rúbrica y los tests, sin IA generativa): pendiente de revisión docente",
    ("teacher", "draft"): "Borrador editado por el equipo docente: pendiente de aprobación",
}
APPROVED_LABEL = "Feedback revisado y aprobado por el equipo docente"


def label_of(draft: FeedbackDraft) -> str:
    return APPROVED_LABEL if draft.status == "approved" else LABELS[(draft.source, draft.status)]


def draft_out(draft: FeedbackDraft) -> FeedbackDraftOut:
    return FeedbackDraftOut(
        id=draft.id, submission_id=draft.submission_id, submission_revision=draft.submission_revision, version=draft.version,
        source=draft.source, status=draft.status, label=label_of(draft), body=draft.body, rubric=list(draft.rubric or []),
        check_results=dict(draft.check_results or {}), created_at=draft.created_at, approved_at=draft.approved_at,
    )


def published_out(draft: FeedbackDraft) -> PublishedFeedbackOut:
    return PublishedFeedbackOut(version=draft.version, label=APPROVED_LABEL, body=draft.body, approved_at=draft.approved_at)


def versions(db: Session, submission_id) -> list[FeedbackDraft]:
    query = select(FeedbackDraft).where(FeedbackDraft.submission_id == submission_id).order_by(FeedbackDraft.version)
    return list(db.scalars(query))


def load_draft(db: Session, draft_id) -> FeedbackDraft:
    draft = db.get(FeedbackDraft, draft_id)
    if not draft:
        raise UserFacingError(status.HTTP_404_NOT_FOUND, "feedback_draft_not_found", "No encontramos este borrador de feedback.")
    return draft


def _next_version(db: Session, submission_id) -> int:
    return (db.scalar(select(func.max(FeedbackDraft.version)).where(FeedbackDraft.submission_id == submission_id)) or 0) + 1


def _results(submission: Submission) -> tuple[int, int]:
    results = submission.check_results or {}
    passed, total = results.get("passed"), results.get("total")
    if not isinstance(passed, int) or not isinstance(total, int) or total <= 0:
        raise UserFacingError(status.HTTP_409_CONFLICT, "feedback_without_results",
                              "Esta entrega no tiene resultados de tests: no se puede generar un borrador. Registra antes los resultados.")
    return passed, total


def compose(assignment: Assignment, submission: Submission, now: datetime) -> str:
    """Fixed Spanish template: what the tests say, the delivery state and the rubric criteria to assess."""
    passed, total = _results(submission)
    lines = [f"Feedback sobre «{assignment.title}» (revisión {submission.revision} de la entrega).",
             f"Pruebas automáticas: {passed} de {total} superadas."]
    if passed == total:
        lines.append("Todas las pruebas superadas: la parte comprobable está completa.")
    elif passed == 0:
        lines.append("Ninguna prueba superada: revisa primero los requisitos básicos del enunciado.")
    else:
        lines.append(f"Quedan {total - passed} pruebas por superar: revisa qué casos fallan antes de la siguiente entrega.")
    if delivery_state(assignment, submission, now) == "late":
        lines.append("La entrega llegó fuera de plazo.")
    rubric = [str(c) for c in (assignment.rubric or [])]
    if rubric:
        lines.append("Criterios de la rúbrica que valorará el equipo docente:")
        lines.extend(f"- {criterion}" for criterion in rubric)
    lines.append("Borrador automático: lo revisa y aprueba el equipo docente antes de publicarse.")
    return "\n".join(lines)


def generate(db: Session, p: Principal, assignment: Assignment, submission: Submission) -> FeedbackDraft:
    body = compose(assignment, submission, utcnow())
    draft = FeedbackDraft(
        submission_id=submission.id, submission_revision=submission.revision, version=_next_version(db, submission.id),
        source="template", status="draft", body=body, rubric=[str(c) for c in (assignment.rubric or [])],
        check_results=dict(submission.check_results), created_by=p.user.id,
    )
    db.add(draft)
    db.flush()
    audit.record(db, p, "feedback.draft_generated", "submission", str(submission.id), version=draft.version,
                 submission_revision=draft.submission_revision, source="template")
    db.commit()
    return draft


def _require_latest(db: Session, draft: FeedbackDraft) -> None:
    if _next_version(db, draft.submission_id) - 1 != draft.version:
        raise UserFacingError(status.HTTP_409_CONFLICT, "feedback_outdated",
                              "Hay una versión más reciente de este feedback. Vuelve a cargarla antes de continuar.")


def edit(db: Session, p: Principal, draft: FeedbackDraft, body: str, expected_version: int) -> FeedbackDraft:
    """An edit never overwrites: it creates a new teacher version with the same provenance."""
    _require_latest(db, draft)
    if expected_version != draft.version:
        raise UserFacingError(status.HTTP_409_CONFLICT, "feedback_outdated",
                              "Hay una versión más reciente de este feedback. Vuelve a cargarla antes de continuar.")
    new = FeedbackDraft(
        submission_id=draft.submission_id, submission_revision=draft.submission_revision, version=draft.version + 1,
        source="teacher", status="draft", body=body, rubric=list(draft.rubric or []), check_results=dict(draft.check_results or {}),
        created_by=p.user.id,
    )
    db.add(new)
    db.flush()
    audit.record(db, p, "feedback.draft_edited", "submission", str(draft.submission_id), version=new.version,
                 previous_version=draft.version)
    db.commit()
    return new


def approve(db: Session, p: Principal, draft: FeedbackDraft, submission: Submission, expected_revision: int) -> FeedbackDraft:
    """Only the latest version of the current submission revision can be published, and only by a person."""
    _require_latest(db, draft)
    if draft.status == "approved":
        raise UserFacingError(status.HTTP_409_CONFLICT, "feedback_already_approved", "Esta versión del feedback ya está aprobada.")
    if expected_revision != submission.revision or draft.submission_revision != submission.revision:
        raise UserFacingError(status.HTTP_409_CONFLICT, "feedback_stale",
                              "La entrega ha cambiado desde este borrador. Genera uno nuevo con la revisión actual.")
    draft.status, draft.approved_by, draft.approved_at = "approved", p.user.id, utcnow()
    audit.record(db, p, "feedback.approved", "submission", str(submission.id), version=draft.version,
                 submission_revision=submission.revision, source=draft.source)
    db.commit()
    return draft


def published(db: Session, submission_id) -> FeedbackDraft | None:
    query = (select(FeedbackDraft).where(FeedbackDraft.submission_id == submission_id, FeedbackDraft.status == "approved")
             .order_by(FeedbackDraft.version.desc()))
    return db.scalars(query).first()
