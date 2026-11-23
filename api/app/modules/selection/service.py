import uuid

from fastapi import HTTPException, status
from sqlalchemy import func, select
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
from app.modules.selection.models import SelectionDecision
from app.modules.selection.schemas import SelectionDecisionWrite

# An admission decision can be taken while the application is in selection, or from the waiting list (promotion or final refusal).
DECIDABLE_STAGES = (*SELECTION_STAGES, "lista_espera")
TARGET_STAGE = {"admitida": "admitida", "lista_espera": "lista_espera", "no_admitida": "no_admitida"}
# Fixed CRM text: the free-text reason stays in the decision record, never in the history other profiles read.
CRM_TEXT = {
    "admitida": "Selección terminada: admitida y matriculada en la cohorte {cohort}",
    "lista_espera": "Selección terminada: en lista de espera",
    "no_admitida": "Selección terminada: no admitida en esta convocatoria",
}


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


def decide(db: Session, actor: Principal, application_id: uuid.UUID, body: SelectionDecisionWrite) -> SelectionDecision:
    """Records one human admission decision, with its enrollment (when admitting), CRM entry and audit event, in one transaction.

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

    now = utcnow()
    cohort: Cohort | None = None
    enrollment: Enrollment | None = None
    if body.decision == "admitida":
        cohort = _check_cohort(db, application, call, body.cohort_id or "")
        _check_places(db, call)
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
    )
    db.commit()
    return decision
