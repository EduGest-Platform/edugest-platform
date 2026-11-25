import uuid
from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from app.core import audit
from app.core.authz import Principal
from app.core.db import utcnow
from app.core.errors import UserFacingError
from app.modules.admissions.models import Application, ApplicationEvent
from app.modules.catalog.models import Call, Cohort
from app.modules.learning.models import Enrollment
from app.modules.preselection.service import SELECTION_STAGES, STAGE_LABELS
from app.modules.requirements.service import require_access
from app.modules.selection.models import SelectionApproval, SelectionDecision
from app.modules.selection.authority import signature_authority
from app.modules.selection.schemas import (
    WAITING_ORDER_BASIS, OwnOutcomeEnrollment, OwnSelectionOutcome, SelectionCandidate, SelectionDecisionWrite, SelectionOverview, WaitingListEntry,
)

# An admission decision can be taken while the application is in selection, or from the waiting list (promotion or final refusal).
DECIDABLE_STAGES = (*SELECTION_STAGES, "lista_espera")
TARGET_STAGE = {"admitida": "admitida", "lista_espera": "lista_espera", "no_admitida": "no_admitida"}
APPROVAL_CRM_TEXT = "Voto de decisión final registrado: falta el acuerdo de otra persona"
# Fixed CRM text: the free-text reason stays in the decision record, never in the history other profiles read.
CRM_TEXT = {
    "admitida": "Selección terminada: admitida y matriculada en la cohorte {cohort}",
    "lista_espera": "Selección terminada: en lista de espera",
    "no_admitida": "Selección terminada: no admitida en esta convocatoria",
}


def own_selection_outcome(db: Session, actor: Principal, application_id: uuid.UUID) -> OwnSelectionOutcome:
    person_id = actor.user.person_id
    if person_id is None:
        raise _own_application_not_found()

    applied = (
        select(SelectionDecision.decision, SelectionDecision.to_stage, SelectionDecision.occurred_at,
               SelectionDecision.cohort_id, SelectionDecision.enrollment_id)
        .where(SelectionDecision.application_id == Application.id)
        .order_by(SelectionDecision.occurred_at.desc(), SelectionDecision.id.desc())
        .limit(1)
        .correlate(Application)
        .lateral()
    )
    result = db.execute(
        select(Application.id, Application.stage, applied.c.decision, applied.c.occurred_at,
               Enrollment.id.label("enrollment_id"), Enrollment.cohort_id, Enrollment.estado)
        .outerjoin(applied, (applied.c.decision == Application.stage) & (applied.c.to_stage == Application.stage))
        .outerjoin(Enrollment, and_(
            applied.c.decision == "admitida",
            Enrollment.id == applied.c.enrollment_id,
            Enrollment.cohort_id == applied.c.cohort_id,
            Enrollment.application_id == Application.id,
            Enrollment.person_id == Application.person_id,
        ))
        .where(Application.id == application_id, Application.person_id == person_id)
    ).one_or_none()
    if result is None:
        raise _own_application_not_found()
    enrollment = None
    if result.enrollment_id is not None:
        enrollment = OwnOutcomeEnrollment(enrollment_id=result.enrollment_id, cohort_id=result.cohort_id, status=result.estado)
    return OwnSelectionOutcome(
        application_id=result.id, stage=result.stage, outcome=result.decision, decided_at=result.occurred_at, enrollment=enrollment,
    )


def _own_application_not_found() -> UserFacingError:
    return UserFacingError(status.HTTP_404_NOT_FOUND, "application_not_found", "No encontramos una candidatura para tu cuenta.")


def waiting_list_order(db: Session, call_id: str) -> list[tuple[Application, datetime]]:
    """Waiting list of a call, first to enter first in line (provisional criterion, not yet confirmed by the foundation).

    The moment of entry is the latest «lista_espera» decision of the application; without one, its last update.
    The order is only a proposal: nobody is promoted by it, a person always decides.
    """
    entered_at = (
        select(func.max(SelectionDecision.occurred_at))
        .where(SelectionDecision.application_id == Application.id, SelectionDecision.decision == "lista_espera")
        .correlate(Application)
        .scalar_subquery()
    )
    since = func.coalesce(entered_at, Application.updated_at).label("since")
    rows = db.execute(
        select(Application, since)
        .where(Application.call_id == call_id, Application.stage == "lista_espera")
        .order_by(since, Application.codigo)
    ).all()
    return [(application, entered_at) for application, entered_at in rows]


def selection_overview(db: Session, actor: Principal, call: Call) -> SelectionOverview:
    """Places of the call next to the applications still in selection and the ordered waiting list (read only)."""
    require_selection_access(db, actor, "selection.read", call)
    stage_of_each = db.execute(select(Application.stage, func.count()).where(Application.call_id == call.id).group_by(Application.stage)).all()
    totals = {stage: total for stage, total in stage_of_each}
    admitted = totals.get("admitida", 0)
    candidates = db.scalars(
        select(Application).where(Application.call_id == call.id, Application.stage.in_(SELECTION_STAGES)).order_by(Application.codigo)
    ).all()
    queue = waiting_list_order(db, call.id)
    audit.record(db, actor, "selection.overview_viewed", "call", call.id, in_selection=len(candidates), waiting=len(queue))
    db.commit()
    return SelectionOverview(
        call_id=call.id, plazas=call.plazas, admitted=admitted, free_places=max(call.plazas - admitted, 0),
        in_selection=len(candidates), waiting=len(queue),
        candidates=[
            SelectionCandidate(application_id=a.id, codigo=a.codigo, stage=a.stage, stage_label=STAGE_LABELS.get(a.stage, a.stage)) for a in candidates
        ],
        waiting_list=[
            WaitingListEntry(position=position, application_id=a.id, codigo=a.codigo, since=entered_at, is_next=position == 1)
            for position, (a, entered_at) in enumerate(queue, start=1)
        ],
        waiting_order_basis=WAITING_ORDER_BASIS, waiting_order_confirmed=False,
    )


def _conflict(code: str, message: str) -> UserFacingError:
    return UserFacingError(status.HTTP_409_CONFLICT, code, message)


def require_selection_access(db: Session, actor: Principal, permission: str, call: Call) -> None:
    """Same role + scope rule as pre-selection, with a message a non-technical person can act on."""
    try:
        require_access(db, actor, permission, call)
    except HTTPException as denied:
        raise UserFacingError(
            denied.status_code, "no_scope_permission",
            "No tienes permiso para consultar o decidir la admisión de candidaturas de esta convocatoria. "
            "Si crees que deberías tenerlo, pídeselo a administración.",
        ) from denied


def _check_stage(application: Application, decision: str) -> None:
    stage = application.stage
    if stage in DECIDABLE_STAGES:
        if stage == "lista_espera" and decision == "lista_espera":
            raise _conflict("already_on_waiting_list", "Esta candidatura ya está en la lista de espera. Puedes admitirla o marcarla como no admitida.")
        return
    if stage in ("admitida", "no_admitida"):
        raise _conflict(
            "selection_ended",
            f"La selección de esta candidatura ya terminó (está en «{STAGE_LABELS.get(stage, stage)}»). "
            "Revisa el historial del expediente; si hay que corregirla, consúltalo con administración.",
        )
    if stage == "retirada":
        raise _conflict("application_withdrawn", "La persona retiró su candidatura, así que no se puede decidir su admisión.")
    raise _conflict(
        "selection_not_started",
        f"Todavía no se puede decidir la admisión porque la candidatura está en «{STAGE_LABELS.get(stage, stage)}». "
        "Primero hay que terminar la preselección y convocarla a selección.",
    )


def _check_cohort(db: Session, application: Application, call: Call, cohort_id: str) -> Cohort:
    cohort = db.get(Cohort, cohort_id)
    if cohort is None or cohort.call_id != call.id:
        # One answer for «does not exist» and «belongs to another call»: the response never confirms a cohort outside the call.
        raise UserFacingError(
            422, "cohort_not_in_call",
            "Esa cohorte no corresponde a la convocatoria de esta candidatura. Elige una de las cohortes de la convocatoria; "
            "si todavía no hay ninguna, pídele a administración que la cree.",
        )
    if db.scalar(select(Enrollment.id).where(Enrollment.person_id == application.person_id, Enrollment.cohort_id == cohort.id)):
        raise _conflict("already_enrolled", "Esta persona ya está matriculada en esa cohorte, así que no se puede admitir de nuevo.")
    return cohort


def _check_places(db: Session, call: Call) -> None:
    admitted = db.scalar(select(func.count()).select_from(Application).where(Application.call_id == call.id, Application.stage == "admitida"))
    if admitted >= call.plazas:
        raise _conflict(
            "no_places_left",
            f"La convocatoria ya tiene todas sus plazas cubiertas ({admitted} de {call.plazas}). "
            "Puedes dejar a la persona en lista de espera.",
        )


def pending_approvals(db: Session, application_id: uuid.UUID) -> list[SelectionApproval]:
    query = select(SelectionApproval).where(SelectionApproval.application_id == application_id, SelectionApproval.decision_id.is_(None))
    return list(db.scalars(query.order_by(SelectionApproval.occurred_at, SelectionApproval.id)))


def _agreeing(approvals: list[SelectionApproval], body: SelectionDecisionWrite) -> list[SelectionApproval]:
    """Votes for exactly the same outcome (and, when admitting, the same cohort)."""
    return [a for a in approvals if a.decision == body.decision and a.cohort_id == (body.cohort_id if body.decision == "admitida" else None)]


def decide(db: Session, actor: Principal, application_id: uuid.UUID, body: SelectionDecisionWrite) -> SelectionDecision | list[SelectionApproval]:
    """Records one person's vote and, when `call.selection_quorum` different people agree, applies the decision with its
    enrollment (when admitting), CRM entry and audit event, in one transaction.

    Returns the SelectionDecision when it was applied, or the pending votes when more people still have to agree.
    The application and its call are locked together, so two people admitting at the same time cannot exceed the places of the call.
    """
    row = db.execute(
        select(Application, Call).join(Call, Call.id == Application.call_id).where(Application.id == application_id).with_for_update(of=(Application, Call))
    ).first()
    if not row:
        raise UserFacingError(status.HTTP_404_NOT_FOUND, "application_not_found", "No encontramos esta candidatura. Vuelve a la lista y ábrela de nuevo.")
    application, call = row
    require_selection_access(db, actor, "selection.decide", call)
    _check_stage(application, body.decision)
    # Checked on every vote, so a wrong cohort or a full call is caught before anyone waits for a second person.
    cohort = _check_cohort(db, application, call, body.cohort_id or "") if body.decision == "admitida" else None
    if cohort:
        _check_places(db, call)

    pending = pending_approvals(db, application.id)
    if any(a.actor_user_id == actor.user.id for a in pending):
        raise _conflict("already_approved", "Ya registraste tu voto sobre esta candidatura. La decisión necesita a otra persona distinta.")
    now = utcnow()
    vote = SelectionApproval(application_id=application.id, decision=body.decision, cohort_id=cohort.id if cohort else None,
                             reason=body.reason, actor_user_id=actor.user.id, occurred_at=now,
                             authority=signature_authority(actor, call.program_id, call.id))
    db.add(vote)
    agreeing = [*_agreeing(pending, body), vote]
    if len(agreeing) < call.selection_quorum:
        return _wait_for_quorum(db, actor, application, call, body, [*pending, vote], now)
    decision = _apply(db, actor, application, call, body, cohort, now)
    # Every open vote is closed by this decision, outvoted ones included: an old vote must never count towards a later
    # decision (for example a promotion from the waiting list). They stay linked to the decision they were part of.
    for approval in [*pending, vote]:
        approval.decision_id = decision.id
    db.commit()
    return decision


def _wait_for_quorum(db: Session, actor: Principal, application: Application, call: Call, body: SelectionDecisionWrite,
                     votes: list[SelectionApproval], now: datetime) -> list[SelectionApproval]:
    """Keeps the vote and moves the application to «pendiente de decisión» (a waiting-list promotion stays on the list)."""
    stage_changed = application.stage in SELECTION_STAGES and application.stage != "pendiente_decision_humana"
    if stage_changed:
        application.stage, application.updated_at = "pendiente_decision_humana", now
    db.add(ApplicationEvent(application_id=application.id, tipo="cambio_etapa" if stage_changed else "nota", resumen=APPROVAL_CRM_TEXT,
                            actor_user_id=actor.user.id, occurred_at=now))
    db.flush()
    audit.record(db, actor, "selection.approved", "application", str(application.id), codigo=application.codigo, decision=body.decision,
                 votes=len(votes), quorum=call.selection_quorum)
    db.commit()
    return votes


def _apply(db: Session, actor: Principal, application: Application, call: Call, body: SelectionDecisionWrite, cohort: Cohort | None, now: datetime) -> SelectionDecision:
    # Promoting someone who is not first in the waiting list is allowed (a person decides), but it is audited.
    out_of_waiting_order = False
    if application.stage == "lista_espera" and body.decision == "admitida":
        queue = waiting_list_order(db, call.id)
        out_of_waiting_order = bool(queue) and queue[0][0].id != application.id

    enrollment: Enrollment | None = None
    if cohort:
        enrollment = Enrollment(person_id=application.person_id, cohort_id=cohort.id, application_id=application.id, estado="activa")
        db.add(enrollment)
        db.flush()

    from_stage = application.stage
    to_stage = TARGET_STAGE[body.decision]
    decision = SelectionDecision(
        application_id=application.id, decision=body.decision, from_stage=from_stage, to_stage=to_stage, reason=body.reason,
        actor_user_id=actor.user.id, occurred_at=now, cohort_id=cohort.id if cohort else None, enrollment_id=enrollment.id if enrollment else None,
    )
    db.add(decision)
    if to_stage != from_stage:
        application.stage = to_stage
        application.updated_at = now
    db.add(
        ApplicationEvent(
            application_id=application.id, tipo="cambio_etapa", resumen=CRM_TEXT[body.decision].format(cohort=cohort.id if cohort else ""),
            actor_user_id=actor.user.id, occurred_at=now,
        )
    )
    db.flush()
    audit.record(
        db, actor, "selection.decided", "application", str(application.id),
        codigo=application.codigo, decision=body.decision, from_stage=from_stage, to_stage=to_stage, cohort_id=cohort.id if cohort else None,
        out_of_waiting_order=out_of_waiting_order, quorum=call.selection_quorum,
    )
    return decision
