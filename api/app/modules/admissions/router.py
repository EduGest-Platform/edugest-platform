import uuid

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, or_, select

from app.core import audit
from app.core.authz import Scope
from app.core.deps import DB, CurrentPrincipal, OptionalPrincipal
from app.modules.admissions.models import Application, ApplicationEvent
from app.modules.admissions.schemas import (
    ApplicationCreate,
    ApplicationDetail,
    ApplicationList,
    ApplicationReceipt,
    ApplicationSelfView,
    ApplicationSummary,
    EventCreate,
    EventOut,
    PersonOut,
    Stage,
)
from app.modules.admissions.service import create_application
from app.modules.catalog.models import Call
from app.modules.identity.models import Person, User

router = APIRouter(tags=["admissions"])


def _summary(a: Application, person: Person, call: Call) -> ApplicationSummary:
    return ApplicationSummary(
        id=a.id, codigo=a.codigo, legacy_ref=a.legacy_ref, call_id=a.call_id, program_id=call.program_id, stage=a.stage,
        person=PersonOut(id=person.id, display_name=person.display_name, email=person.email), created_at=a.created_at, updated_at=a.updated_at,
    )


def _load(db: DB, application_id: uuid.UUID) -> tuple[Application, Person, Call]:
    row = db.execute(select(Application, Person, Call).join(Person, Person.id == Application.person_id).join(Call, Call.id == Application.call_id).where(Application.id == application_id)).first()
    if not row:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Candidatura no encontrada")
    a, person, call = row
    return a, person, call


@router.post("/applications", response_model=ApplicationReceipt, status_code=201, summary="Inscripción pública: crea o reutiliza la ficha de persona")
def post_application(body: ApplicationCreate, db: DB, p: OptionalPrincipal) -> ApplicationReceipt:
    a = create_application(db, body, p)
    return ApplicationReceipt(id=a.id, codigo=a.codigo, call_id=a.call_id, stage=a.stage, created_at=a.created_at)


@router.get("/applications", response_model=ApplicationList, summary="Expedientes dentro del ámbito del usuario (captación / selección / administración)")
def list_applications(
    p: CurrentPrincipal,
    db: DB,
    call_id: str | None = None,
    stage: Stage | None = None,
    q: str | None = Query(None, max_length=80, description="Busca por nombre, correo o código"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> ApplicationList:
    is_global, programs, calls = p.scopes_for("applications.read")
    if not (is_global or programs or calls):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "No tienes permiso para consultar expedientes")
    base = select(Application, Person, Call).join(Person, Person.id == Application.person_id).join(Call, Call.id == Application.call_id)
    if not is_global:
        base = base.where(or_(Call.program_id.in_(programs), Call.id.in_(calls)))
    if call_id:
        base = base.where(Application.call_id == call_id)
    if stage:
        base = base.where(Application.stage == stage)
    if q:
        like = f"%{q.strip().lower()}%"
        base = base.where(or_(func.lower(Person.display_name).like(like), Person.email.like(like), func.lower(Application.codigo).like(like)))
    total = db.scalar(select(func.count()).select_from(base.subquery())) or 0
    rows = db.execute(base.order_by(Application.created_at.desc(), Application.codigo.desc()).limit(limit).offset(offset)).all()
    return ApplicationList(items=[_summary(*r) for r in rows], total=total)


@router.get("/applications/{application_id}", response_model=ApplicationDetail, summary="Ficha del expediente con historial CRM")
def get_application(application_id: uuid.UUID, p: CurrentPrincipal, db: DB) -> ApplicationDetail:
    a, person, call = _load(db, application_id)
    p.require("applications.read", Scope(program_id=call.program_id, call_id=call.id))
    events = db.execute(
        select(ApplicationEvent, User.display_name).outerjoin(User, User.id == ApplicationEvent.actor_user_id).where(ApplicationEvent.application_id == a.id).order_by(ApplicationEvent.occurred_at)
    ).all()
    audit.record(db, p, "application.viewed", "application", str(a.id), codigo=a.codigo)
    db.commit()
    return ApplicationDetail(
        **_summary(a, person, call).model_dump(),
        motivacion=a.motivacion,
        disponibilidad=a.disponibilidad,
        events=[EventOut(id=e.id, tipo=e.tipo, canal=e.canal, resumen=e.resumen, actor=name, occurred_at=e.occurred_at) for e, name in events],
    )


@router.post("/applications/{application_id}/events", response_model=EventOut, status_code=201, summary="Registrar contacto, nota o recordatorio en el CRM")
def post_event(application_id: uuid.UUID, body: EventCreate, p: CurrentPrincipal, db: DB) -> EventOut:
    a, _, call = _load(db, application_id)
    p.require("applications.crm", Scope(program_id=call.program_id, call_id=call.id))
    ev = ApplicationEvent(application_id=a.id, tipo=body.tipo, canal=body.canal, resumen=body.resumen.strip(), actor_user_id=p.user.id)
    db.add(ev)
    db.flush()
    audit.record(db, p, "application.event_added", "application", str(a.id), codigo=a.codigo, tipo=body.tipo)
    db.commit()
    return EventOut(id=ev.id, tipo=ev.tipo, canal=ev.canal, resumen=ev.resumen, actor=p.user.display_name, occurred_at=ev.occurred_at)


@router.get("/me/applications", response_model=list[ApplicationSelfView], summary="Candidaturas propias de la persona autenticada")
def my_applications(p: CurrentPrincipal, db: DB) -> list[ApplicationSelfView]:
    if not p.user.person_id:
        return []
    rows = db.execute(select(Application, Call).join(Call, Call.id == Application.call_id).where(Application.person_id == p.user.person_id).order_by(Application.created_at.desc())).all()
    return [ApplicationSelfView(id=a.id, codigo=a.codigo, call_id=a.call_id, call_nombre=c.nombre, stage=a.stage, created_at=a.created_at, updated_at=a.updated_at) for a, c in rows]
