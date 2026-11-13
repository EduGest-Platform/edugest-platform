from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core import audit
from app.core.authz import Principal
from app.modules.admissions.models import Application, ApplicationEvent
from app.modules.admissions.schemas import ApplicationCreate
from app.modules.catalog.models import Call
from app.modules.identity.models import Person


def create_application(db: Session, body: ApplicationCreate, actor: Principal | None) -> Application:
    # Row lock on the call: serialises the per-call code counter.
    call = db.scalar(select(Call).where(Call.id == body.call_id).with_for_update())
    if not call:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Convocatoria no encontrada")
    if call.estado != "abierta":
        raise HTTPException(status.HTTP_409_CONFLICT, "La convocatoria no admite inscripciones")

    person = db.scalar(select(Person).where(Person.email == body.email))
    reused = person is not None
    if person is None:
        person = Person(display_name=body.nombre, email=body.email, is_synthetic=True)
        db.add(person)
        db.flush()
    elif db.scalar(select(Application.id).where(Application.person_id == person.id, Application.call_id == call.id)):
        raise HTTPException(status.HTTP_409_CONFLICT, "Ya existe una candidatura con este correo en esta convocatoria")

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
    except IntegrityError as e:  # concurrent duplicate submission
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Ya existe una candidatura con este correo en esta convocatoria") from e
    db.add(ApplicationEvent(application_id=app.id, tipo="creada", resumen="Inscripción recibida por formulario", actor_user_id=actor.user.id if actor else None))
    audit.record(db, actor, "application.created", "application", str(app.id), codigo=app.codigo, call_id=call.id, person_reused=reused)
    db.commit()
    return app
