import uuid
from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import audit
from app.core.authz import Principal
from app.core.errors import UserFacingError
from app.core.db import utcnow
from app.modules.admissions.models import Application, ApplicationEvent
from app.modules.catalog.models import Call
from app.modules.preselection.models import PreselectionDecision
from app.modules.preselection.schemas import PreselectionDecisionWrite, SilenceEvidence
from app.modules.requirements.models import RequirementReview
from app.modules.requirements.service import require_access

# Pre-selection is open while an application is in one of these stages; requirement reviews run in parallel and never block it.
PRESELECTION_STAGES = ("enviada", "requisitos_en_revision")
SELECTION_STAGES = ("convocada", "evaluacion_en_curso", "pendiente_decision_humana")
# PO decision 19/11/2026: a person can withdraw at any point of pre-selection or selection. After admission,
# leaving is an enrollment withdrawal (baja de matrícula), recorded on the enrollment, not here.
WITHDRAWAL_STAGES = PRESELECTION_STAGES + SELECTION_STAGES
STAGE_LABELS = {
    "enviada": "enviada", "requisitos_en_revision": "requisitos en revisión", "convocada": "convocada a selección",
    "evaluacion_en_curso": "evaluación en curso", "pendiente_decision_humana": "pendiente de decisión", "admitida": "admitida",
    "lista_espera": "lista de espera", "no_admitida": "no admitida", "retirada": "retirada",
}
RESOLVED_REQUIREMENT_RESULTS = ("met", "exception_approved")
# New stage per decision. A silence review that is postponed leaves the stage as it is.
TARGET_STAGE = {"convocada": "convocada", "retirada_expresa": "retirada", "silencio_confirmado": "retirada", "silencio_reprogramado": None}
CRM_TEXT = {
    "convocada": "Preselección terminada: convocada a selección",
    "retirada_expresa": "Retirada expresa de la persona",
    "silencio_confirmado": "Preselección terminada: abandono por silencio confirmado por una persona",
    "silencio_reprogramado": "Revisión de silencio reprogramada por una persona",
}
SILENCE_DECISIONS = ("silencio_confirmado", "silencio_reprogramado")


def silence_evidence(call: Call, events: list[ApplicationEvent], decisions: list[PreselectionDecision], now: datetime) -> SilenceEvidence:
    """Counts unanswered contact attempts since the last answer or postponement.

    Only attempts recorded as «sin_respuesta» count: an attempt with no recorded result is never evidence of silence.
    """
    restarts = [e.occurred_at for e in events if e.tipo == "contacto" and e.resultado == "respondida"]
    restarts += [d.occurred_at for d in decisions if d.decision == "silencio_reprogramado"]
    restart = max(restarts, default=None)
    attempts = [e.occurred_at for e in events if e.tipo == "contacto" and e.resultado == "sin_respuesta" and (restart is None or e.occurred_at > restart)]
    last_attempt = max(attempts, default=None)
    days = (now - last_attempt).days if last_attempt else None
    met = len(attempts) >= call.silence_max_contacts and days is not None and days >= call.silence_days
    return SilenceEvidence(
        unanswered_attempts=len(attempts), last_attempt_at=last_attempt, days_without_response=days,
        silence_days=call.silence_days, silence_max_contacts=call.silence_max_contacts,
        silence_warning_contacts=call.silence_warning_contacts, alert_level=_alert_level(len(attempts), met, call), threshold_met=met,
    )


def _alert_level(unanswered: int, action_threshold_met: bool, call: Call) -> str | None:
    """«accion» when a person must decide; «leve» as soon as the warning count is reached (no waiting days)."""
    if action_threshold_met:
        return "accion"
    if unanswered >= call.silence_warning_contacts:
        return "leve"
    return None


def application_silence_evidence(db: Session, application: Application, call: Call, now: datetime) -> SilenceEvidence:
    events = list(db.scalars(select(ApplicationEvent).where(ApplicationEvent.application_id == application.id, ApplicationEvent.tipo == "contacto")))
    decisions = list(db.scalars(select(PreselectionDecision).where(PreselectionDecision.application_id == application.id)))
    return silence_evidence(call, events, decisions, now)


def _conflict(code: str, message: str) -> UserFacingError:
    return UserFacingError(status.HTTP_409_CONFLICT, code, message)


def require_preselection_access(db: Session, actor: Principal, permission: str, call: Call) -> None:
    """Same role + scope rule as requirement reviews, with a message a non-technical person can act on."""
    try:
        require_access(db, actor, permission, call)
    except HTTPException as denied:
        raise UserFacingError(
            denied.status_code, "no_scope_permission",
            "No tienes permiso para consultar o decidir sobre candidaturas de esta convocatoria. "
            "Si crees que deberías tenerlo, pídeselo a administración.",
        ) from denied


def _check_stage(application: Application, decision: str) -> None:
    stage = application.stage
    if decision == "retirada_expresa":
        if stage in WITHDRAWAL_STAGES:
            return
        if stage == "admitida":
            raise _conflict(
                "withdrawal_after_admission",
                "Esta persona ya está admitida. Si deja la formación, registra la baja en su matrícula, no aquí.",
            )
        raise _conflict(
            "withdrawal_not_available",
            f"No se puede registrar la retirada porque la candidatura está en «{STAGE_LABELS.get(stage, stage)}». "
            "La retirada solo se registra durante la preselección o la selección.",
        )
    if stage not in PRESELECTION_STAGES:
        raise _conflict(
            "preselection_ended",
            f"La preselección de esta candidatura ya terminó (ahora está en «{STAGE_LABELS.get(stage, stage)}»), "
            "así que esta decisión ya no se puede tomar. Revisa el historial del expediente.",
        )


def _check_silence(decision: str, silence: SilenceEvidence) -> None:
    progress = (
        f"Lleva {silence.unanswered_attempts} intentos sin respuesta (la alerta de acción pide {silence.silence_max_contacts})"
        + (f" y han pasado {silence.days_without_response} días desde el último (se piden {silence.silence_days})." if silence.days_without_response is not None else ".")
    )
    if decision == "silencio_confirmado" and not silence.threshold_met:
        raise _conflict(
            "silence_threshold_not_met",
            f"Todavía no se puede confirmar el silencio. {progress} Sigue intentando el contacto; "
            "si la persona ha dicho que se retira, registra una retirada expresa.",
        )
    if decision == "silencio_reprogramado" and silence.alert_level is None:
        raise _conflict(
            "no_silence_alert",
            f"No hay ninguna alerta de silencio que reprogramar. {progress}",
        )


def _unresolved_requirement_reviews(db: Session, application: Application) -> int:
    reviews = db.scalars(select(RequirementReview.result).where(RequirementReview.application_id == application.id))
    return sum(1 for result in reviews if result not in RESOLVED_REQUIREMENT_RESULTS)


def decide(db: Session, actor: Principal, application_id: uuid.UUID, body: PreselectionDecisionWrite) -> PreselectionDecision:
    """Records one human decision about the end of pre-selection, with its CRM entry and audit event, in one transaction."""
    row = db.execute(
        select(Application, Call).join(Call, Call.id == Application.call_id).where(Application.id == application_id).with_for_update(of=Application)
    ).first()
    if not row:
        raise UserFacingError(status.HTTP_404_NOT_FOUND, "application_not_found", "No encontramos esta candidatura. Vuelve a la lista y ábrela de nuevo.")
    application, call = row
    require_preselection_access(db, actor, "preselection.decide", call)
    _check_stage(application, body.decision)

    now = utcnow()
    evidence: dict = {}
    if body.decision in SILENCE_DECISIONS:
        silence = application_silence_evidence(db, application, call, now)
        _check_silence(body.decision, silence)
        evidence = silence.model_dump(mode="json")
    elif body.decision == "convocada":
        # Open requirement reviews do not block the call to selection; they are recorded so the decision stays explainable.
        evidence = {"unresolved_requirement_reviews": _unresolved_requirement_reviews(db, application)}

    from_stage = application.stage
    to_stage = TARGET_STAGE[body.decision] or from_stage
    decision = PreselectionDecision(
        application_id=application.id, decision=body.decision, from_stage=from_stage, to_stage=to_stage,
        reason=body.reason, actor_user_id=actor.user.id, occurred_at=now, evidence=evidence,
    )
    db.add(decision)
    if to_stage != from_stage:
        application.stage = to_stage
        application.updated_at = now
    db.add(
        ApplicationEvent(
            application_id=application.id, tipo="cambio_etapa" if to_stage != from_stage else "nota",
            resumen=CRM_TEXT[body.decision], actor_user_id=actor.user.id, occurred_at=now,
        )
    )
    db.flush()
    audit.record(db, actor, "preselection.decided", "application", str(application.id), codigo=application.codigo, decision=body.decision, from_stage=from_stage, to_stage=to_stage)
    db.commit()
    return decision
