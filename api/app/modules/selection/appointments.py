"""Citations and evaluation evidence, scoped to the application's call."""

import uuid
from typing import Annotated, Literal

from fastapi import APIRouter
from pydantic import AwareDatetime, BaseModel, ConfigDict, StringConstraints, model_validator
from sqlalchemy import select

from app.core import audit
from app.core.authz import Scope
from app.core.db import utcnow
from app.core.deps import DB, CurrentPrincipal
from app.core.errors import UserFacingError
from app.modules.admissions.models import Application
from app.modules.catalog.models import Call
from app.modules.preselection.service import SELECTION_STAGES
from app.modules.selection.models import SelectionAppointment

Kind = Literal["group_day", "individual_interview"]
Outcome = Literal["attended", "no_show"]

router = APIRouter(prefix="/applications/{application_id}/selection-appointments", tags=["selection"])
_ERRORS = {403: {"description": "Sin permiso sobre el ámbito"}, 404: {"description": "No encontrado"}}
_WRITE_ERRORS = {**_ERRORS, 409: {"description": "La candidatura o cita ya no permite el cambio solicitado"}}


class AppointmentCreate(BaseModel):
    kind: Kind
    scheduled_at: AwareDatetime
    location: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=250)] | None = None
    previous_id: uuid.UUID | None = None


class AppointmentOutcome(BaseModel):
    result: Outcome
    conclusions: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1000)] | None = None
    assessment: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)] | None = None

    @model_validator(mode="after")
    def validate_notes(self):
        if self.result == "no_show" and (self.conclusions is not None or self.assessment is not None):
            raise ValueError("Las conclusiones y la valoración requieren asistencia.")
        return self


class AppointmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    previous_id: uuid.UUID | None
    kind: Kind
    state: Literal["scheduled", "attended", "no_show", "rescheduled"]
    scheduled_at: AwareDatetime
    location: str | None
    created_at: AwareDatetime
    recorded_at: AwareDatetime | None
    conclusions: str | None
    assessment: str | None


class AppointmentList(BaseModel):
    can_edit: bool
    items: list[AppointmentOut]


def scoped_application(db: DB, actor: CurrentPrincipal, application_id: uuid.UUID, *,
                       write: bool = False) -> tuple[Application, Scope]:
    permission = "selection.decide" if write else "selection.read"
    if not all(any(actor.scopes_for(perm)) for perm in ("applications.read", permission)):
        raise UserFacingError(403, "no_scope_permission", "No tienes permiso para gestionar citas de selección.")
    query = select(Application, Call).join(Call, Call.id == Application.call_id).where(Application.id == application_id)
    if write:
        # Also serializes with final decisions and with writes to other appointments for this dossier.
        query = query.with_for_update(of=Application)
    row = db.execute(query).one_or_none()
    if row is None:
        raise UserFacingError(404, "application_not_found", "No encontramos esta candidatura.")
    application, call = row
    # Appointment evidence stays inside the dossier, even when other roles can vote from a call overview.
    scope = Scope(program_id=call.program_id, call_id=call.id)
    if not actor.can("applications.read", scope) or not actor.can(permission, scope):
        audit.record(db, actor, "application.access_denied", "application", str(application_id), permission=permission)
        db.commit()
        raise UserFacingError(403, "no_scope_permission", "No tienes permiso para gestionar citas en esta convocatoria.")
    if write and application.stage not in SELECTION_STAGES:
        raise UserFacingError(409, "selection_appointment_stage", "La candidatura debe estar en selección para cambiar una cita.")
    return application, scope


def find_appointment(db: DB, application_id: uuid.UUID, appointment_id: uuid.UUID) -> SelectionAppointment:
    visit = db.scalar(select(SelectionAppointment).where(
        SelectionAppointment.application_id == application_id, SelectionAppointment.id == appointment_id,
    ))
    if visit is None:
        raise UserFacingError(404, "selection_appointment_not_found", "No encontramos esta cita en la candidatura.")
    return visit


@router.get("", response_model=AppointmentList, responses=_ERRORS, summary="Consultar las citaciones de selección")
def list_appointments(application_id: uuid.UUID, p: CurrentPrincipal, db: DB) -> AppointmentList:
    application, scope = scoped_application(db, p, application_id)
    rows = db.scalars(select(SelectionAppointment).where(SelectionAppointment.application_id == application_id)
                      .order_by(SelectionAppointment.scheduled_at.desc(), SelectionAppointment.id)).all()
    audit.record(db, p, "selection.appointments_viewed", "application", str(application_id))
    view = AppointmentList(can_edit=application.stage in SELECTION_STAGES and p.can("selection.decide", scope),
                           items=[AppointmentOut.model_validate(row) for row in rows])
    db.commit()
    return view


@router.post("", response_model=AppointmentOut, status_code=201, responses=_WRITE_ERRORS,
             summary="Agendar una jornada o entrevista, o enlazar una nueva fecha a una citación anterior")
def create_appointment(application_id: uuid.UUID, body: AppointmentCreate, p: CurrentPrincipal, db: DB) -> AppointmentOut:
    scoped_application(db, p, application_id, write=True)
    if body.scheduled_at <= utcnow():
        raise UserFacingError(422, "selection_appointment_past", "Elige una fecha y hora futuras.")
    previous = None
    if body.previous_id is not None:
        previous = find_appointment(db, application_id, body.previous_id)
        successor = db.scalar(select(SelectionAppointment.id).where(SelectionAppointment.previous_id == previous.id))
        if (previous.kind != body.kind or previous.state not in {"scheduled", "no_show"} or successor is not None
                or body.scheduled_at == previous.scheduled_at):
            raise UserFacingError(409, "selection_appointment_replacement", "Esta cita no admite esa reprogramación.")
    pending = db.scalar(select(SelectionAppointment.id).where(
        SelectionAppointment.application_id == application_id, SelectionAppointment.kind == body.kind,
        SelectionAppointment.state == "scheduled",
    ))
    if pending is not None and (previous is None or previous.id != pending):
        raise UserFacingError(409, "selection_appointment_duplicate", "Ya hay una cita pendiente de este tipo. Reprograma la cita existente.")
    if previous is not None and previous.state == "scheduled":
        previous.state = "rescheduled"
        db.flush()
    appointment = SelectionAppointment(application_id=application_id, created_by=p.user.id, **body.model_dump())
    db.add(appointment)
    db.flush()
    audit.record(db, p, "selection.appointment_scheduled", "application", str(application_id),
                 appointment_id=str(appointment.id), kind=appointment.kind,
                 previous_id=str(body.previous_id) if body.previous_id is not None else None)
    view = AppointmentOut.model_validate(appointment)
    db.commit()
    return view


@router.post("/{appointment_id}/outcome", response_model=AppointmentOut, responses=_WRITE_ERRORS,
             summary="Registrar asistencia o ausencia y, cuando proceda, conclusiones y valoración")
def record_appointment_outcome(application_id: uuid.UUID, appointment_id: uuid.UUID, body: AppointmentOutcome,
                               p: CurrentPrincipal, db: DB) -> AppointmentOut:
    scoped_application(db, p, application_id, write=True)
    appointment = find_appointment(db, application_id, appointment_id)
    now = utcnow()
    if appointment.state != "scheduled" or appointment.scheduled_at > now:
        raise UserFacingError(409, "selection_appointment_outcome", "Solo puedes registrar el resultado de una cita pendiente cuya hora ya llegó.")
    appointment.state = body.result
    appointment.conclusions = body.conclusions
    appointment.assessment = body.assessment
    appointment.recorded_at = now
    appointment.recorded_by = p.user.id
    audit.record(db, p, "selection.appointment_outcome_recorded", "application", str(application_id),
                 appointment_id=str(appointment.id), result=body.result)
    view = AppointmentOut.model_validate(appointment)
    db.commit()
    return view
