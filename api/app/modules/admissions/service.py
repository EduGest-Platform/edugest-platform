from collections.abc import Callable

from fastapi import HTTPException, status
from psycopg.errors import UniqueViolation
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core import audit
from app.core.authz import Principal
from app.modules.admissions.identity_reviews import lock_email, matching_records
from app.modules.admissions.models import PUBLIC_ORIGIN, Application, ApplicationEvent, IdentityReview
from app.modules.admissions.schemas import IntakeFields
from app.modules.catalog.models import Call
from app.modules.catalog.publication_policy import require_published
from app.modules.identity.models import Person


def _duplicates_constraint(error: IntegrityError, constraint_name: str) -> bool:
    cause = error.orig
    return isinstance(cause, UniqueViolation) and cause.diag.constraint_name == constraint_name


def _duplicate_application() -> HTTPException:
    return HTTPException(status.HTTP_409_CONFLICT, "Ya existe una candidatura con este correo en esta convocatoria")


def _applied_to_call(db: Session, email: str, call_id: str) -> bool:
    query = select(Application.id).join(Person, Person.id == Application.person_id)
    return db.scalar(query.where(Person.email == email, Application.call_id == call_id).limit(1)) is not None


def _own_record(db: Session, actor: Principal | None, email: str) -> Person | None:
    """The record of the signed-in person applying with their own email: the session proves who they are."""
    if actor is None or actor.user.person_id is None:
        return None
    person = db.get(Person, actor.user.person_id)
    return person if person is not None and person.email == email else None


def _new_person(db: Session, body: IntakeFields) -> Person:
    person = Person(display_name=body.nombre, email=body.email, is_synthetic=True)
    db.add(person)
    db.flush()
    return person


ORIGIN_LABELS = {
    "correo": "correo", "telefono": "teléfono", "derivacion": "derivación", "registro_manual": "registro manual", "redes": "redes",
}


def _creation_summary(origin_channel: str) -> str:
    if origin_channel == PUBLIC_ORIGIN:
        return "Inscripción recibida por formulario"
    return f"Alta registrada por el equipo. Canal de origen: {ORIGIN_LABELS[origin_channel]}"


def create_application(
    db: Session, body: IntakeFields, actor: Principal | None, origin_channel: str = PUBLIC_ORIGIN,
    authorize_call: Callable[[Call], None] | None = None,
) -> Application:
    """The single intake path: public and manual applications share its call checks and duplicate control.

    The caller validates the synthetic data confirmation (the schema). `authorize_call` runs on the locked call row and
    raises when the actor may not write to it.
    """
    if origin_channel != PUBLIC_ORIGIN and authorize_call is None:
        raise ValueError("A manual intake needs its call authorisation")
    # Row lock on the call: serialises the per-call code counter.
    # A caller may have loaded this call already: re-read it, or the code and the status would be the ones from before the lock.
    call = db.scalar(select(Call).where(Call.id == body.call_id).with_for_update().execution_options(populate_existing=True))
    if authorize_call is not None and call is not None:
        authorize_call(call)
    # Share the call lock with publication changes; check before creating any person/application.
    require_published(call)
    if call.estado != "abierta":
        raise HTTPException(status.HTTP_409_CONFLICT, "La convocatoria no admite inscripciones")

    lock_email(db, body.email)
    if _applied_to_call(db, body.email, call.id):
        raise _duplicate_application()
    # Only on the public form can the sender be the applicant.
    own = _own_record(db, actor, body.email) if origin_channel == PUBLIC_ORIGIN else None
    person = own or _new_person(db, body)
    candidates = [] if own else matching_records(db, person)

    app = Application(
        codigo=f"{call.codigo_prefix}-{call.next_seq:04d}",
        person_id=person.id,
        call_id=call.id,
        stage="enviada",
        motivacion=body.motivacion,
        disponibilidad=body.disponibilidad,
        acepta_datos_sinteticos=True,
        origin_channel=origin_channel,
        created_by=actor.user.id if actor else None,
    )
    call.next_seq += 1
    db.add(app)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        if _duplicates_constraint(exc, "uq_application_person_call"):
            raise _duplicate_application() from exc
        raise
    if candidates:
        db.add(IdentityReview(application_id=app.id, original_person_id=person.id, candidate_person_ids=candidates))
    db.add(ApplicationEvent(application_id=app.id, tipo="creada", resumen=_creation_summary(origin_channel), actor_user_id=actor.user.id if actor else None))
    audit.record(db, actor, "application.created", "application", str(app.id), codigo=app.codigo, call_id=call.id,
                 origin_channel=origin_channel, own_record=own is not None, identity_review=bool(candidates))
    db.commit()
    return app
