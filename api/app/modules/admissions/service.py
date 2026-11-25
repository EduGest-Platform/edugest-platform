from fastapi import HTTPException, status
from psycopg.errors import UniqueViolation
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core import audit
from app.core.authz import Principal
from app.modules.admissions.models import Application, ApplicationEvent
from app.modules.admissions.schemas import ApplicationCreate
from app.modules.catalog.models import Call
from app.modules.catalog.publication_policy import require_published
from app.modules.identity.models import Person


def _duplicates_constraint(error: IntegrityError, constraint_name: str) -> bool:
    cause = error.orig
    return isinstance(cause, UniqueViolation) and cause.diag.constraint_name == constraint_name


def _duplicate_application() -> HTTPException:
    return HTTPException(status.HTTP_409_CONFLICT, "Ya existe una candidatura con este correo en esta convocatoria")


def _find_or_create_person(db: Session, body: ApplicationCreate) -> tuple[Person, bool]:
    """Return the Person for this email and whether it already existed (one expediente per human being)."""
    person = db.scalar(select(Person).where(Person.email == body.email))
    if person is not None:
        return person, True
    try:
        with db.begin_nested():  # savepoint: a lost race must not undo the call lock or the transaction
            person = Person(display_name=body.nombre, email=body.email, is_synthetic=True)
            db.add(person)
    except IntegrityError as exc:
        if not _duplicates_constraint(exc, "ix_person_email"):
            raise
        # Another request may have created the same Person after our lookup: reuse it. If no Person with this email
        # exists, the violation was something else and must surface, not be disguised as a race.
        existing = db.scalar(select(Person).where(Person.email == body.email))
        if existing is None:
            raise
        return existing, True
    return person, False


def create_application(db: Session, body: ApplicationCreate, actor: Principal | None) -> Application:
    # Row lock on the call: serialises the per-call code counter.
    call = db.scalar(select(Call).where(Call.id == body.call_id).with_for_update())
    # Share the call lock with publication changes; check before creating any person/application.
    require_published(call)
    if call.estado != "abierta":
        raise HTTPException(status.HTTP_409_CONFLICT, "La convocatoria no admite inscripciones")

    person, reused = _find_or_create_person(db, body)
    if reused and db.scalar(select(Application.id).where(Application.person_id == person.id, Application.call_id == call.id)):
        raise _duplicate_application()

    app = Application(
        codigo=f"{call.codigo_prefix}-{call.next_seq:04d}",
        person_id=person.id,
        call_id=call.id,
        stage="enviada",
        motivacion=body.motivacion,
        disponibilidad=body.disponibilidad,
        acepta_datos_sinteticos=body.acepta_datos_sinteticos,
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
    db.add(ApplicationEvent(application_id=app.id, tipo="creada", resumen="Inscripción recibida por formulario", actor_user_id=actor.user.id if actor else None))
    audit.record(db, actor, "application.created", "application", str(app.id), codigo=app.codigo, call_id=call.id, person_reused=reused)
    db.commit()
    return app
