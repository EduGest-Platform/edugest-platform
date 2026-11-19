import uuid
from collections import defaultdict
from collections.abc import Iterable
from datetime import datetime

from fastapi import APIRouter, Path, status
from sqlalchemy import select

from app.core import audit
from app.core.authz import PRESELECTION_POLICY_PERMISSION, Scope
from app.core.errors import UserFacingError
from app.core.db import utcnow
from app.core.deps import DB, CurrentPrincipal
from app.modules.admissions.models import Application, ApplicationEvent
from app.modules.catalog.models import Call
from app.modules.identity.models import Person, User
from app.modules.preselection.models import PreselectionDecision
from app.modules.preselection.schemas import (
    PreselectionDecisionList,
    PreselectionDecisionOut,
    PreselectionDecisionWrite,
    PreselectionPolicy,
    SilenceReviewItem,
    SilenceReviewList,
)
from app.modules.preselection.service import PRESELECTION_STAGES, decide, require_preselection_access, silence_evidence

router = APIRouter(tags=["preselection"])

CallId = Path(max_length=30)
_ERRORS = {403: {"description": "Sin permiso sobre el ámbito"}, 404: {"description": "No encontrado"}}


def _load_call(db: DB, call_id: str) -> Call:
    call = db.get(Call, call_id)
    if not call:
        raise UserFacingError(status.HTTP_404_NOT_FOUND, "call_not_found", "No encontramos esta convocatoria. Vuelve a la lista de convocatorias.")
    return call


def _policy(call: Call) -> PreselectionPolicy:
    return PreselectionPolicy(silence_days=call.silence_days, silence_max_contacts=call.silence_max_contacts, silence_warning_contacts=call.silence_warning_contacts)


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
        raise UserFacingError(status.HTTP_404_NOT_FOUND, "application_not_found", "No encontramos esta candidatura. Vuelve a la lista y ábrela de nuevo.")
    application, call = row
    require_preselection_access(db, p, "preselection.read", call)
    decisions = list(db.scalars(select(PreselectionDecision).where(PreselectionDecision.application_id == application.id).order_by(PreselectionDecision.occurred_at)))
    ids = {d.actor_user_id for d in decisions}
    names = {u.id: u.display_name for u in db.scalars(select(User).where(User.id.in_(ids)))} if ids else {}
    audit.record(db, p, "preselection.decisions_viewed", "application", str(application.id), codigo=application.codigo)
    db.commit()
    return PreselectionDecisionList(application_id=application.id, items=[_out(d, names.get(d.actor_user_id)) for d in decisions])


def group_by_application(rows: Iterable[ApplicationEvent | PreselectionDecision]) -> dict[uuid.UUID, list]:
    """Groups contact events or decisions by application in a single pass."""
    grouped: dict[uuid.UUID, list] = defaultdict(list)
    for row in rows:
        grouped[row.application_id].append(row)
    return grouped


def silence_review_items(
    call: Call,
    applications: list[tuple[Application, str]],
    events: Iterable[ApplicationEvent],
    decisions: Iterable[PreselectionDecision],
    now: datetime,
) -> list[SilenceReviewItem]:
    """Applications with a silence alert («leve» or «accion»), each paired with the person's name.

    Each application only sees its own contacts and decisions.

    Events and decisions are grouped once, so the cost grows linearly with the call instead of
    re-scanning every record for every application.
    """
    events_by_application = group_by_application(events)
    decisions_by_application = group_by_application(decisions)
    items = []
    for application, display_name in applications:
        evidence = silence_evidence(call, events_by_application.get(application.id, []), decisions_by_application.get(application.id, []), now)
        if evidence.alert_level:
            items.append(
                SilenceReviewItem(application_id=application.id, codigo=application.codigo, display_name=display_name, stage=application.stage, evidence=evidence)
            )
    return items


@router.get(
    "/calls/{call_id}/silence-review",
    response_model=SilenceReviewList,
    responses=_ERRORS,
    summary="Candidaturas en preselección con alerta de silencio leve o de acción; una persona revisa (no se cierra nada solo)",
)
def silence_review(p: CurrentPrincipal, db: DB, call_id: str = CallId) -> SilenceReviewList:
    call = _load_call(db, call_id)
    require_preselection_access(db, p, "preselection.read", call)
    applications = [
        (application, display_name)
        for application, display_name in db.execute(
            select(Application, Person.display_name)
            .join(Person, Person.id == Application.person_id)
            .where(Application.call_id == call.id, Application.stage.in_(PRESELECTION_STAGES))
            .order_by(Application.codigo)
        )
    ]
    ids = [a.id for a, _ in applications]
    events = list(db.scalars(select(ApplicationEvent).where(ApplicationEvent.application_id.in_(ids), ApplicationEvent.tipo == "contacto"))) if ids else []
    decisions = list(db.scalars(select(PreselectionDecision).where(PreselectionDecision.application_id.in_(ids)))) if ids else []
    items = silence_review_items(call, applications, events, decisions, utcnow())
    audit.record(db, p, "preselection.silence_review_viewed", "call", call.id, pending=len(items))
    db.commit()
    return SilenceReviewList(call_id=call.id, items=items)


@router.get(
    "/calls/{call_id}/preselection-policy",
    response_model=PreselectionPolicy,
    responses=_ERRORS,
    summary="Política de silencio de la convocatoria (por defecto: alerta leve a los 2 intentos; alerta de acción a los 4 intentos y 30 días)",
)
def get_preselection_policy(p: CurrentPrincipal, db: DB, call_id: str = CallId) -> PreselectionPolicy:
    call = _load_call(db, call_id)
    require_preselection_access(db, p, "preselection.read", call)
    return _policy(call)


@router.put(
    "/calls/{call_id}/preselection-policy",
    response_model=PreselectionPolicy,
    responses=_ERRORS,
    summary="Editar la política de silencio de una convocatoria (administración y captación). No cambia decisiones ya tomadas",
)
def put_preselection_policy(body: PreselectionPolicy, p: CurrentPrincipal, db: DB, call_id: str = CallId) -> PreselectionPolicy:
    call = _load_call(db, call_id)
    if not p.can(PRESELECTION_POLICY_PERMISSION, Scope(program_id=call.program_id, call_id=call.id)):
        raise UserFacingError(
            status.HTTP_403_FORBIDDEN, "no_policy_permission",
            "Solo administración y captación de este programa pueden cambiar la política de silencio. Pídeselo a una de ellas.",
        )
    before = _policy(call)
    call.silence_days, call.silence_max_contacts, call.silence_warning_contacts = body.silence_days, body.silence_max_contacts, body.silence_warning_contacts
    audit.record(
        db, p, "call.preselection_policy_updated", "call", call.id,
        **{f"{key}_before": value for key, value in before.model_dump().items()}, **body.model_dump(),
    )
    db.commit()
    return body
