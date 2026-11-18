import uuid
from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import audit
from app.core.authz import Principal
from app.core.db import utcnow
from app.modules.admissions.models import Application, ApplicationEvent
from app.modules.catalog.models import Call
from app.modules.preselection.models import PreselectionDecision
from app.modules.preselection.schemas import PreselectionDecisionWrite, SilenceEvidence
from app.modules.requirements.models import RequirementReview
from app.modules.requirements.service import require_access

# Pre-selection is open while an application is in one of these stages; requirement reviews run in parallel and never block it.
PRESELECTION_STAGES = ("enviada", "requisitos_en_revision")
RESOLVED_REQUIREMENT_RESULTS = ("met", "exception_approved")
# New stage per decision. A silence review that is postponed leaves the stage as it is.
TARGET_STAGE = {"convocada": "convocada", "retirada_expresa": "retirada", "silencio_confirmado": "retirada", "silencio_reprogramado": None}
CRM_TEXT = {
    "convocada": "Preselección terminada: convocada a selección",
    "retirada_expresa": "Preselección terminada: retirada expresa de la persona",
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
        silence_days=call.silence_days, silence_max_contacts=call.silence_max_contacts, threshold_met=met,
    )


def application_silence_evidence(db: Session, application: Application, call: Call, now: datetime) -> SilenceEvidence:
    events = list(db.scalars(select(ApplicationEvent).where(ApplicationEvent.application_id == application.id, ApplicationEvent.tipo == "contacto")))
    decisions = list(db.scalars(select(PreselectionDecision).where(PreselectionDecision.application_id == application.id)))
    return silence_evidence(call, events, decisions, now)


def _conflict(detail: str) -> HTTPException:
    return HTTPException(status.HTTP_409_CONFLICT, detail)


def _unresolved_requirement_reviews(db: Session, application: Application) -> int:
    reviews = db.scalars(select(RequirementReview.result).where(RequirementReview.application_id == application.id))
    return sum(1 for result in reviews if result not in RESOLVED_REQUIREMENT_RESULTS)


def decide(db: Session, actor: Principal, application_id: uuid.UUID, body: PreselectionDecisionWrite) -> PreselectionDecision:
    """Records one human decision about the end of pre-selection, with its CRM entry and audit event, in one transaction."""
    row = db.execute(
        select(Application, Call).join(Call, Call.id == Application.call_id).where(Application.id == application_id).with_for_update(of=Application)
    ).first()
    if not row:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Candidatura no encontrada")
    application, call = row
    require_access(db, actor, "preselection.decide", call)
    if application.stage not in PRESELECTION_STAGES:
        raise _conflict("La preselección de esta candidatura ya ha terminado")

    now = utcnow()
    evidence: dict = {}
    if body.decision in SILENCE_DECISIONS:
        silence = application_silence_evidence(db, application, call, now)
        if not silence.threshold_met:
            raise _conflict("Todavía no se cumple el umbral de silencio de la convocatoria")
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
