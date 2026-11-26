import uuid

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, or_, select

from app.core import audit
from app.core.authz import Scope
from app.core.deps import DB, CurrentPrincipal, OptionalPrincipal
from app.core.text import LIKE_ESCAPE, escape_like
from app.modules.admissions import identity_reviews, manual_intake
from app.modules.admissions.models import Application, ApplicationEvent
from app.modules.admissions.next_actions import eligible_owners, next_action_out, owner_names, rejection_reason
from app.modules.admissions.schemas import (
    ApplicationCreate,
    ApplicationDetail,
    ApplicationList,
    ApplicationReceipt,
    ApplicationSelfView,
    ApplicationSummary,
    CrmOwnerOut,
    EventCreate,
    EventOut,
    IdentityDecisionCreate,
    IdentityReviewOut,
    ManualApplicationCreate,
    ManualIntakeCallOut,
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
        origin_channel=a.origin_channel,
        person=PersonOut(id=person.id, display_name=person.display_name, email=person.email), created_at=a.created_at, updated_at=a.updated_at,
    )


APPLICATION_NOT_FOUND = "Candidatura no encontrada"
OUT_OF_SCOPE = (
    "Esta candidatura pertenece a una convocatoria que no tienes asignada. "
    "Si necesitas verla, pide acceso a administración."
)


def _load(db: DB, application_id: uuid.UUID) -> tuple[Application, Person, Call]:
    row = db.execute(select(Application, Person, Call).join(Person, Person.id == Application.person_id).join(Call, Call.id == Application.call_id).where(Application.id == application_id)).first()
    if not row:
        raise HTTPException(status.HTTP_404_NOT_FOUND, APPLICATION_NOT_FOUND)
    a, person, call = row
    return a, person, call


def _load_in_scope(db: DB, p: CurrentPrincipal, perm: str, application_id: uuid.UUID) -> tuple[Application, Person, Call]:
    """Loads an application only if `perm` covers its program or call.

    PO decision (19/11/2026): an application outside the caller's scope answers 403 with a message that says why
    and what to do, and the denied attempt is audited (ids and codes only) so administration can spot probing.
    A caller without `perm` in any scope gets 403 before any lookup, so it cannot tell known from unknown ids.
    """
    is_global, programs, calls = p.scopes_for(perm)
    if not (is_global or programs or calls):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "No tienes permiso sobre este ámbito")
    a, person, call = _load(db, application_id)
    if not p.can(perm, Scope(program_id=call.program_id, call_id=call.id)):
        audit.record(db, p, "application.access_denied", "application", str(a.id), codigo=a.codigo, permission=perm)
        db.commit()
        raise HTTPException(status.HTTP_403_FORBIDDEN, OUT_OF_SCOPE)
    return a, person, call


@router.post("/applications", response_model=ApplicationReceipt, status_code=201,
             responses={404: {"description": "Published offer not found"}},
             summary="Inscripción pública en oferta publicada: crea una ficha de persona sin unirla a otras")
def post_application(body: ApplicationCreate, db: DB, p: OptionalPrincipal) -> ApplicationReceipt:
    a = create_application(db, body, p)
    return ApplicationReceipt(id=a.id, codigo=a.codigo, call_id=a.call_id, stage=a.stage, created_at=a.created_at)


@router.get("/manual-intake/calls", response_model=list[ManualIntakeCallOut], summary="Convocatorias donde puedes registrar candidaturas a mano")
def list_manual_intake_calls(p: CurrentPrincipal, db: DB) -> list[ManualIntakeCallOut]:
    return [ManualIntakeCallOut(id=c.id, nombre=c.nombre) for c in manual_intake.registrable_calls(db, p)]


@router.post("/manual-intake/applications", response_model=ApplicationReceipt, status_code=201,
             responses={404: {"description": "Published offer not found"}},
             summary="Registrar a mano una candidatura llegada fuera del formulario, con su canal de origen")
def post_manual_application(body: ManualApplicationCreate, db: DB, p: CurrentPrincipal) -> ApplicationReceipt:
    a = manual_intake.register_application(db, p, body)
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
        like = f"%{escape_like(q.strip().lower())}%"
        base = base.where(
            or_(
                func.lower(Person.display_name).like(like, escape=LIKE_ESCAPE),
                Person.email.like(like, escape=LIKE_ESCAPE),
                func.lower(Application.codigo).like(like, escape=LIKE_ESCAPE),
            )
        )
    total = db.scalar(select(func.count()).select_from(base.subquery())) or 0
    rows = db.execute(base.order_by(Application.created_at.desc(), Application.codigo.desc()).limit(limit).offset(offset)).all()
    return ApplicationList(items=[_summary(*r) for r in rows], total=total)


@router.get("/applications/{application_id}", response_model=ApplicationDetail, summary="Ficha del expediente con historial CRM")
def get_application(application_id: uuid.UUID, p: CurrentPrincipal, db: DB) -> ApplicationDetail:
    a, person, call = _load_in_scope(db, p, "applications.read", application_id)
    events = db.execute(
        select(ApplicationEvent, User.display_name).outerjoin(User, User.id == ApplicationEvent.actor_user_id).where(ApplicationEvent.application_id == a.id).order_by(ApplicationEvent.occurred_at)
    ).all()
    names = owner_names(db, [e for e, _ in events])
    registrar = db.get(User, a.created_by) if a.created_by else None
    outs = [
        EventOut(id=e.id, tipo=e.tipo, canal=e.canal, resultado=e.resultado, resumen=e.resumen, actor=name, occurred_at=e.occurred_at,
                 next_action=next_action_out(e, names))
        for e, name in events
    ]
    audit.record(db, p, "application.viewed", "application", str(a.id), codigo=a.codigo)
    db.commit()
    return ApplicationDetail(
        **_summary(a, person, call).model_dump(),
        registered_by=registrar.display_name if registrar else None,
        motivacion=a.motivacion,
        disponibilidad=a.disponibilidad,
        events=outs,
        next_action=next((o.next_action for o in reversed(outs) if o.next_action), None),
    )


@router.get("/applications/{application_id}/crm-owners", response_model=list[CrmOwnerOut], summary="Personal que puede ser responsable de una próxima acción")
def list_crm_owners(application_id: uuid.UUID, p: CurrentPrincipal, db: DB) -> list[CrmOwnerOut]:
    _, _, call = _load_in_scope(db, p, "applications.crm", application_id)
    return [CrmOwnerOut(user_id=u.id, display_name=u.display_name) for u in eligible_owners(db, call)]


@router.get("/applications/{application_id}/identity-review", response_model=IdentityReviewOut, summary="Aviso de posible duplicado de una candidatura")
def get_identity_review(application_id: uuid.UUID, p: CurrentPrincipal, db: DB) -> IdentityReviewOut:
    a, _, _ = _load_in_scope(db, p, identity_reviews.REVIEW_PERMISSION, application_id)
    out = identity_reviews.review_out(db, p, a)
    if out.status != "sin_coincidencias":
        audit.record(db, p, "application.identity_review_viewed", "application", str(a.id), codigo=a.codigo, matches_shown=len(out.matches))
        db.commit()
    return out


@router.post("/applications/{application_id}/identity-review", response_model=IdentityReviewOut, status_code=201,
             summary="Decidir si un posible duplicado es la misma persona (queda registrado quién, cuándo y por qué)")
def post_identity_review(application_id: uuid.UUID, body: IdentityDecisionCreate, p: CurrentPrincipal, db: DB) -> IdentityReviewOut:
    a, _, _ = _load_in_scope(db, p, identity_reviews.REVIEW_PERMISSION, application_id)
    return identity_reviews.decide(db, p, a, body)


@router.post("/applications/{application_id}/events", response_model=EventOut, status_code=201, summary="Registrar contacto, nota o recordatorio en el CRM")
def post_event(application_id: uuid.UUID, body: EventCreate, p: CurrentPrincipal, db: DB) -> EventOut:
    a, _, call = _load_in_scope(db, p, "applications.crm", application_id)
    if body.resultado and body.tipo != "contacto":
        raise HTTPException(422, "El resultado solo se registra en eventos de contacto")
    if body.next_action and body.tipo != "contacto":
        raise HTTPException(422, "La próxima acción solo se registra en eventos de contacto")
    if body.next_action and (reason := rejection_reason(db, call, body.next_action)):
        raise HTTPException(422, reason)
    ev = ApplicationEvent(application_id=a.id, tipo=body.tipo, canal=body.canal, resultado=body.resultado, resumen=body.resumen.strip(), actor_user_id=p.user.id)
    if body.next_action:
        ev.next_action = body.next_action.description
        ev.next_action_owner_id = body.next_action.owner_user_id
        ev.next_action_due_on = body.next_action.due_on
    db.add(ev)
    db.flush()
    audit.record(db, p, "application.event_added", "application", str(a.id), codigo=a.codigo, tipo=body.tipo)
    db.commit()
    return EventOut(id=ev.id, tipo=ev.tipo, canal=ev.canal, resultado=ev.resultado, resumen=ev.resumen, actor=p.user.display_name, occurred_at=ev.occurred_at,
                    next_action=next_action_out(ev, owner_names(db, [ev])))


@router.get("/me/applications", response_model=list[ApplicationSelfView], summary="Candidaturas propias de la persona autenticada")
def my_applications(p: CurrentPrincipal, db: DB) -> list[ApplicationSelfView]:
    if not p.user.person_id:
        return []
    rows = db.execute(select(Application, Call).join(Call, Call.id == Application.call_id).where(Application.person_id == p.user.person_id).order_by(Application.created_at.desc())).all()
    return [ApplicationSelfView(id=a.id, codigo=a.codigo, call_id=a.call_id, call_nombre=c.nombre, stage=a.stage, created_at=a.created_at, updated_at=a.updated_at) for a, c in rows]
