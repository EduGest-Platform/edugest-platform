import uuid

from fastapi import APIRouter, Path, Response, status
from sqlalchemy import select

from app.core import audit
from app.core.authz import SELECTION_POLICY_PERMISSION, Scope
from app.core.deps import DB, CurrentPrincipal
from app.core.errors import UserFacingError
from app.modules.admissions.models import Application
from app.modules.catalog.models import Call
from app.modules.identity.models import User
from app.modules.selection.models import SelectionApproval, SelectionDecision
from app.modules.selection.schemas import (
    SelectionApprovalOut, SelectionDecisionList, SelectionDecisionOut, SelectionDecisionWrite, SelectionOverview, SelectionPendingOut, SelectionPolicy,
)
from app.modules.selection.service import decide, pending_approvals, require_selection_access, selection_overview

router = APIRouter(tags=["selection"])

_ERRORS = {403: {"description": "Sin permiso sobre el ámbito"}, 404: {"description": "No encontrado"}}


def _out(decision: SelectionDecision, actor_name: str | None) -> SelectionDecisionOut:
    return SelectionDecisionOut(
        id=decision.id, application_id=decision.application_id, decision=decision.decision, from_stage=decision.from_stage,
        to_stage=decision.to_stage, reason=decision.reason, actor=actor_name, occurred_at=decision.occurred_at,
        cohort_id=decision.cohort_id, enrollment_id=decision.enrollment_id,
    )


def _names(db: DB, user_ids: set) -> dict:
    return {u.id: u.display_name for u in db.scalars(select(User).where(User.id.in_(user_ids)))} if user_ids else {}


def _votes_out(db: DB, votes: list[SelectionApproval]) -> list[SelectionApprovalOut]:
    names = _names(db, {v.actor_user_id for v in votes})
    return [SelectionApprovalOut(decision=v.decision, cohort_id=v.cohort_id, reason=v.reason, actor=names.get(v.actor_user_id), occurred_at=v.occurred_at) for v in votes]


@router.post(
    "/applications/{application_id}/selection-decisions",
    response_model=SelectionDecisionOut | SelectionPendingOut,
    status_code=201,
    responses={
        202: {"model": SelectionPendingOut, "description": "Voto registrado; falta que otra persona distinta coincida (quórum)"},
        **_ERRORS,
        409: {"description": "La selección ya terminó, no hay plazas o la persona ya está matriculada en esa cohorte"},
        422: {"description": "Datos no válidos o cohorte que no pertenece a la convocatoria"},
    },
    summary="Votar el fin de la selección: admitir (y matricular), lista de espera o no admitida. Se aplica cuando coinciden las personas del quórum",
)
def post_selection_decision(application_id: uuid.UUID, body: SelectionDecisionWrite, p: CurrentPrincipal, db: DB, response: Response) -> SelectionDecisionOut | SelectionPendingOut:
    result = decide(db, p, application_id, body)
    if isinstance(result, SelectionDecision):
        return _out(result, p.user.display_name)
    response.status_code = status.HTTP_202_ACCEPTED
    application = db.get(Application, application_id)
    call = db.get(Call, application.call_id)
    state = "disagreement" if len({(v.decision, v.cohort_id) for v in result}) > 1 else "pending"
    return SelectionPendingOut(application_id=application.id, state=state, stage=application.stage, quorum=call.selection_quorum, votes=_votes_out(db, result))


@router.get(
    "/applications/{application_id}/selection-decisions",
    response_model=SelectionDecisionList,
    responses=_ERRORS,
    summary="Historial de decisiones de admisión de una candidatura",
)
def list_selection_decisions(application_id: uuid.UUID, p: CurrentPrincipal, db: DB) -> SelectionDecisionList:
    row = db.execute(select(Application, Call).join(Call, Call.id == Application.call_id).where(Application.id == application_id)).first()
    if not row:
        raise UserFacingError(status.HTTP_404_NOT_FOUND, "application_not_found", "No encontramos esta candidatura. Vuelve a la lista y ábrela de nuevo.")
    application, call = row
    require_selection_access(db, p, "selection.read", call)
    decisions = list(db.scalars(select(SelectionDecision).where(SelectionDecision.application_id == application.id).order_by(SelectionDecision.occurred_at)))
    ids = {d.actor_user_id for d in decisions}
    names = {u.id: u.display_name for u in db.scalars(select(User).where(User.id.in_(ids)))} if ids else {}
    audit.record(db, p, "selection.decisions_viewed", "application", str(application.id), codigo=application.codigo)
    db.commit()
    return SelectionDecisionList(application_id=application.id, items=[_out(d, names.get(d.actor_user_id)) for d in decisions],
                                 quorum=call.selection_quorum, pending_votes=_votes_out(db, pending_approvals(db, application.id)))


@router.get(
    "/calls/{call_id}/selection-overview",
    response_model=SelectionOverview,
    responses=_ERRORS,
    summary="Plazas de la convocatoria junto a las candidaturas en selección y la lista de espera ordenada (solo lectura)",
)
def get_selection_overview(p: CurrentPrincipal, db: DB, call_id: str = Path(max_length=30)) -> SelectionOverview:
    call = db.get(Call, call_id)
    if not call:
        raise UserFacingError(status.HTTP_404_NOT_FOUND, "call_not_found", "No encontramos esta convocatoria. Vuelve a la lista de convocatorias.")
    return selection_overview(db, p, call)


def _load_call(db: DB, call_id: str) -> Call:
    call = db.get(Call, call_id)
    if not call:
        raise UserFacingError(status.HTTP_404_NOT_FOUND, "call_not_found", "No encontramos esta convocatoria. Vuelve a la lista de convocatorias.")
    return call


@router.get("/calls/{call_id}/selection-policy", response_model=SelectionPolicy, responses=_ERRORS,
            summary="Regla de decisión de selección de la convocatoria: cuántas personas distintas deben coincidir")
def get_selection_policy(p: CurrentPrincipal, db: DB, call_id: str = Path(max_length=30)) -> SelectionPolicy:
    call = _load_call(db, call_id)
    require_selection_access(db, p, "selection.read", call)
    return SelectionPolicy(selection_quorum=call.selection_quorum)


@router.put("/calls/{call_id}/selection-policy", response_model=SelectionPolicy, responses=_ERRORS,
            summary="Cambiar el quórum de selección de una convocatoria (solo administración, auditado). No cambia decisiones ya tomadas")
def put_selection_policy(body: SelectionPolicy, p: CurrentPrincipal, db: DB, call_id: str = Path(max_length=30)) -> SelectionPolicy:
    call = db.scalar(select(Call).where(Call.id == call_id).with_for_update())  # serialized with votes, which lock the call
    if not call:
        raise UserFacingError(status.HTTP_404_NOT_FOUND, "call_not_found", "No encontramos esta convocatoria. Vuelve a la lista de convocatorias.")
    if not p.can(SELECTION_POLICY_PERMISSION, Scope(program_id=call.program_id, call_id=call.id)):
        raise UserFacingError(status.HTTP_403_FORBIDDEN, "no_policy_permission",
                              "Solo administración puede cambiar cuántas personas deben coincidir en la decisión de selección.")
    before = call.selection_quorum
    call.selection_quorum = body.selection_quorum
    audit.record(db, p, "call.selection_policy_updated", "call", call.id, selection_quorum_before=before, selection_quorum=body.selection_quorum)
    db.commit()
    return body
