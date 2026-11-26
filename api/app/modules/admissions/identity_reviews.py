"""KAN-274: possible duplicates. An email already on file raises a review; only a person links two records.

Scope rule: deciding means comparing the records, so the reviewer needs `applications.crm` on every call each matching
record belongs to. A match outside that scope is only announced, with no detail about it.
"""

import uuid

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from app.core import audit
from app.core.authz import Principal, Scope
from app.core.db import utcnow
from app.modules.admissions.models import Application, ApplicationEvent, IdentityReview
from app.modules.admissions.schemas import (
    IdentityDecisionCreate,
    IdentityMatch,
    IdentityMatchApplication,
    IdentityReviewBlocker,
    IdentityReviewOut,
)
from app.modules.catalog.models import Call, Cohort
from app.modules.identity.models import Person, User
from app.modules.learning.models import Enrollment

REVIEW_PERMISSION = "applications.crm"
# Fixed CRM text: the free-text reason stays in the review record.
CRM_TEXT = {
    "misma_persona": "Revisión de duplicado: se ha confirmado que es la misma persona de otro registro",
    "persona_distinta": "Revisión de duplicado: se ha confirmado que son personas distintas",
}
OUT_OF_SCOPE_MATCH = (
    "Hay una coincidencia en una convocatoria que no tienes asignada. "
    "Tiene que resolver el aviso alguien con acceso a todas las convocatorias implicadas, o administración."
)
EARLIER_REVIEW_PENDING = "Antes hay que resolver el aviso de un registro anterior con el mismo correo."


def lock_email(db: Session, email: str) -> None:
    """Serialises intakes and reviews that share an email, so they cannot miss or move each other's records."""
    db.execute(select(func.pg_advisory_xact_lock(func.hashtextextended(email, 0))))


def has_pending_review(db: Session, application_id: uuid.UUID) -> bool:
    query = select(IdentityReview.application_id).where(IdentityReview.application_id == application_id, IdentityReview.decision.is_(None))
    return db.scalar(query) is not None


def _holds_something():
    """A record matters while it keeps an application, an enrollment or an account."""
    return (
        select(Application.id).where(Application.person_id == Person.id).exists()
        | select(Enrollment.id).where(Enrollment.person_id == Person.id).exists()
        | select(User.id).where(User.person_id == Person.id).exists()
    )


def matching_records(db: Session, person: Person) -> list[uuid.UUID]:
    """Records that already use this email. Read at intake, under the email lock, so all of them are earlier."""
    query = select(Person.id).where(Person.email == person.email, Person.id != person.id, _holds_something())
    return list(db.scalars(query.order_by(Person.created_at, Person.id)))


def _matches(db: Session, review: IdentityReview) -> list[Person]:
    """The records found at intake that still hold something: one linked into another one drops out."""
    query = select(Person).where(Person.id.in_(review.candidate_person_ids), _holds_something())
    return list(db.scalars(query.order_by(Person.created_at, Person.id)))


def _enrollment_scopes(db: Session, person_id: uuid.UUID) -> list[Scope]:
    query = select(Cohort.program_id, Cohort.call_id, Cohort.id).join(Enrollment, Enrollment.cohort_id == Cohort.id)
    rows = db.execute(query.where(Enrollment.person_id == person_id))
    return [Scope(program_id=program_id, call_id=call_id, cohort_id=cohort_id) for program_id, call_id, cohort_id in rows]


def _visible_match(db: Session, actor: Principal, person: Person) -> IdentityMatch | None:
    """The record as this person may see it, or None. The applications checked are exactly the ones returned.

    Fails closed: a record with nothing that gives it a scope (only an account) needs global access.
    """
    query = select(Application, Call.program_id).join(Call, Call.id == Application.call_id)
    applications = db.execute(query.where(Application.person_id == person.id).order_by(Application.codigo)).all()
    scopes = [Scope(program_id=program_id, call_id=a.call_id) for a, program_id in applications] + _enrollment_scopes(db, person.id)
    if scopes:
        allowed = all(actor.can(REVIEW_PERMISSION, scope) for scope in scopes)
    else:
        allowed, _, _ = actor.scopes_for(REVIEW_PERMISSION)
    if not allowed:
        return None
    return IdentityMatch(
        person_id=person.id, display_name=person.display_name,
        applications=[IdentityMatchApplication(application_id=a.id, codigo=a.codigo, call_id=a.call_id, stage=a.stage) for a, _ in applications],
    )


def _visible_matches(db: Session, actor: Principal, matches: list[Person]) -> list[IdentityMatch]:
    return [shown for match in matches if (shown := _visible_match(db, actor, match)) is not None]


def _has_unresolved_identity(db: Session, person_id: uuid.UUID) -> bool:
    query = select(IdentityReview.application_id).where(IdentityReview.original_person_id == person_id, IdentityReview.decision.is_(None))
    return db.scalar(query) is not None


def _blocker(db: Session, matches: list[Person], visible: list[IdentityMatch]) -> IdentityReviewBlocker | None:
    if len(visible) < len(matches):
        return "fuera_de_ambito"
    if any(_has_unresolved_identity(db, m.id) for m in matches):
        return "revision_anterior_pendiente"
    return None


def review_out(db: Session, actor: Principal, application: Application) -> IdentityReviewOut:
    review = db.get(IdentityReview, application.id)
    if review is None:
        return IdentityReviewOut(status="sin_coincidencias")
    original = db.get(Person, review.original_person_id)
    matches = _matches(db, review)
    visible = _visible_matches(db, actor, matches)
    hidden = len(visible) < len(matches)
    if review.decision:
        # The reason was written while comparing the records, so it keeps their scope rule after the decision.
        return IdentityReviewOut(
            status=review.decision, submitted_name=original.display_name, has_hidden_matches=hidden,
            reason=None if hidden else review.reason, decided_by=db.get(User, review.decided_by).display_name, decided_at=review.decided_at,
        )
    return IdentityReviewOut(
        status="pendiente", submitted_name=original.display_name, matches=visible,
        has_hidden_matches=hidden, blocker=_blocker(db, matches, visible),
    )


def _lock_pending_review(db: Session, application: Application) -> IdentityReview:
    """Locks in the same order as the intake (call, then email) and re-reads what the decision depends on."""
    db.execute(
        select(Application, Call).join(Call, Call.id == Application.call_id).where(Application.id == application.id)
        .with_for_update(of=(Application, Call)).execution_options(populate_existing=True)
    ).one()
    lock_email(db, db.get(Person, application.person_id).email)
    query = select(IdentityReview).where(IdentityReview.application_id == application.id).execution_options(populate_existing=True)
    review = db.scalar(query)
    if review is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Esta candidatura no tiene ningún aviso de duplicado")
    if review.decision:
        raise HTTPException(status.HTTP_409_CONFLICT, "Este aviso ya está resuelto. Abre el expediente de nuevo para ver la decisión.")
    return review


def _link(db: Session, application: Application, person_id: uuid.UUID) -> None:
    same_call = select(Application.id).where(Application.person_id == person_id, Application.call_id == application.call_id)
    if db.scalar(same_call) is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Ese registro ya tiene una candidatura en esta convocatoria")
    application.person_id = person_id
    # An identity review is not progress on the application: the waiting list and the applicant read this date.
    flag_modified(application, "updated_at")


def decide(db: Session, actor: Principal, application: Application, body: IdentityDecisionCreate) -> IdentityReviewOut:
    review = _lock_pending_review(db, application)
    matches = _matches(db, review)
    blocker = _blocker(db, matches, _visible_matches(db, actor, matches))
    if blocker == "fuera_de_ambito":
        audit.record(db, actor, "application.identity_review_denied", "application", str(application.id), codigo=application.codigo)
        db.commit()
        raise HTTPException(status.HTTP_403_FORBIDDEN, OUT_OF_SCOPE_MATCH)
    if blocker == "revision_anterior_pendiente":
        raise HTTPException(status.HTTP_409_CONFLICT, EARLIER_REVIEW_PENDING)
    if body.decision == "misma_persona":
        if body.linked_person_id not in {m.id for m in matches}:
            raise HTTPException(422, "Elige uno de los registros que muestra el aviso")
        _link(db, application, body.linked_person_id)
        review.linked_person_id = body.linked_person_id
    review.decision, review.reason = body.decision, body.reason
    review.decided_by, review.decided_at = actor.user.id, utcnow()
    db.add(ApplicationEvent(application_id=application.id, tipo="nota", resumen=CRM_TEXT[body.decision], actor_user_id=actor.user.id))
    audit.record(db, actor, "application.identity_reviewed", "application", str(application.id), codigo=application.codigo, decision=body.decision)
    db.commit()
    return review_out(db, actor, application)
