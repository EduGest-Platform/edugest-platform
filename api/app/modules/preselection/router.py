import uuid

from fastapi import APIRouter, HTTPException, Path, status
from sqlalchemy import select

from app.core import audit
from app.core.authz import Scope
from app.core.db import utcnow
from app.core.deps import DB, CurrentPrincipal
from app.modules.admissions.models import Application, ApplicationEvent
from app.modules.catalog.models import Call
from app.modules.identity.models import User
from app.modules.preselection.models import PreselectionDecision
from app.modules.preselection.schemas import (
    PreselectionDecisionList,
    PreselectionDecisionOut,
    PreselectionDecisionWrite,
    PreselectionPolicy,
    SilenceReviewItem,
    SilenceReviewList,
)
from app.modules.preselection.service import PRESELECTION_STAGES, decide, silence_evidence
from app.modules.requirements.service import require_access

router = APIRouter(tags=["preselection"])

CallId = Path(max_length=30)
_ERRORS = {403: {"description": "Sin permiso sobre el ámbito"}, 404: {"description": "No encontrado"}}


def _load_call(db: DB, call_id: str) -> Call:
    call = db.get(Call, call_id)
    if not call:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Convocatoria no encontrada")
    return call


def _out(decision: PreselectionDecision, actor_name: str | None) -> PreselectionDecisionOut:
    return PreselectionDecisionOut(
        id=decision.id, application_id=decision.application_id, decision=decision.decision, from_stage=decision.from_stage,
        to_stage=decision.to_stage, reason=decision.reason, actor=actor_name, occurred_at=decision.occurred_at, evidence=decision.evidence,
    )


@router.post(
    "/applications/{application_id}/preselection-decisions",
    response_model=PreselectionDecisionOut,
    status_code=201,
    responses={**_ERRORS, 409: {"description": "La preselección ya terminó o no se cumple el umbral de silencio"}},
    summary="Terminar la preselección: convocar a selección, retirada expresa o silencio confirmado por una persona",
)
def post_preselection_decision(application_id: uuid.UUID, body: PreselectionDecisionWrite, p: CurrentPrincipal, db: DB) -> PreselectionDecisionOut:
    decision = decide(db, p, application_id, body)
    return _out(decision, p.user.display_name)


@router.get(
    "/applications/{application_id}/preselection-decisions",
    response_model=PreselectionDecisionList,
    responses=_ERRORS,
    summary="Historial de decisiones de fin de preselección de una candidatura",
)
def list_preselection_decisions(application_id: uuid.UUID, p: CurrentPrincipal, db: DB) -> PreselectionDecisionList:
    row = db.execute(select(Application, Call).join(Call, Call.id == Application.call_id).where(Application.id == application_id)).first()
    if not row:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Candidatura no encontrada")
    application, call = row
    require_access(db, p, "preselection.read", call)
    decisions = list(db.scalars(select(PreselectionDecision).where(PreselectionDecision.application_id == application.id).order_by(PreselectionDecision.occurred_at)))
    ids = {d.actor_user_id for d in decisions}
    names = {u.id: u.display_name for u in db.scalars(select(User).where(User.id.in_(ids)))} if ids else {}
    audit.record(db, p, "preselection.decisions_viewed", "application", str(application.id), codigo=application.codigo)
    db.commit()
    return PreselectionDecisionList(application_id=application.id, items=[_out(d, names.get(d.actor_user_id)) for d in decisions])


@router.get(
    "/calls/{call_id}/silence-review",
    response_model=SilenceReviewList,
    responses=_ERRORS,
    summary="Candidaturas en preselección que han cumplido el umbral de silencio y esperan revisión humana (no se cierra nada solo)",
)
def silence_review(p: CurrentPrincipal, db: DB, call_id: str = CallId) -> SilenceReviewList:
    call = _load_call(db, call_id)
    require_access(db, p, "preselection.read", call)
    applications = list(db.scalars(select(Application).where(Application.call_id == call.id, Application.stage.in_(PRESELECTION_STAGES)).order_by(Application.codigo)))
    ids = [a.id for a in applications]
    events = list(db.scalars(select(ApplicationEvent).where(ApplicationEvent.application_id.in_(ids), ApplicationEvent.tipo == "contacto"))) if ids else []
    decisions = list(db.scalars(select(PreselectionDecision).where(PreselectionDecision.application_id.in_(ids)))) if ids else []
    now = utcnow()
    items = []
    for application in applications:
        evidence = silence_evidence(call, [e for e in events if e.application_id == application.id], [d for d in decisions if d.application_id == application.id], now)
        if evidence.threshold_met:
            items.append(SilenceReviewItem(application_id=application.id, codigo=application.codigo, stage=application.stage, evidence=evidence))
    audit.record(db, p, "preselection.silence_review_viewed", "call", call.id, pending=len(items))
    db.commit()
    return SilenceReviewList(call_id=call.id, items=items)


@router.get(
    "/calls/{call_id}/preselection-policy",
    response_model=PreselectionPolicy,
    responses=_ERRORS,
    summary="Política de silencio de la convocatoria (por defecto 30 días y 4 intentos de contacto)",
)
def get_preselection_policy(p: CurrentPrincipal, db: DB, call_id: str = CallId) -> PreselectionPolicy:
    call = _load_call(db, call_id)
    require_access(db, p, "preselection.read", call)
    return PreselectionPolicy(silence_days=call.silence_days, silence_max_contacts=call.silence_max_contacts)


@router.put(
    "/calls/{call_id}/preselection-policy",
    response_model=PreselectionPolicy,
    responses=_ERRORS,
    summary="Editar la política de silencio de una convocatoria. No cambia decisiones ya tomadas",
)
def put_preselection_policy(body: PreselectionPolicy, p: CurrentPrincipal, db: DB, call_id: str = CallId) -> PreselectionPolicy:
    call = _load_call(db, call_id)
    p.require("calls.configure", Scope(program_id=call.program_id, call_id=call.id))
    before = (call.silence_days, call.silence_max_contacts)
    call.silence_days, call.silence_max_contacts = body.silence_days, body.silence_max_contacts
    audit.record(
        db, p, "call.preselection_policy_updated", "call", call.id,
        silence_days_before=before[0], silence_max_contacts_before=before[1], silence_days=body.silence_days, silence_max_contacts=body.silence_max_contacts,
    )
    db.commit()
    return body
