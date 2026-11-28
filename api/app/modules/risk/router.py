"""Cohort-scoped review of synthetic observations and manual support records."""

import uuid

from fastapi import APIRouter, Query
from sqlalchemy import func, select
from sqlalchemy.orm import aliased

from app.core import audit
from app.core.deps import DB, CurrentPrincipal
from app.core.errors import UserFacingError
from app.modules.identity.models import Person, User
from app.modules.learning.access import require_cohort
from app.modules.learning.models import Enrollment
from app.modules.risk.models import Intervention, RiskAlert
from app.modules.risk.schemas import AlertReviewOut, InterventionOut, InterventionWrite, ReviewState, RiskAlertList, RiskAlertOut

router = APIRouter(tags=["risk"], prefix="/cohorts/{cohort_id}/risk-alerts")
ERRORS = {403: {"description": "Sin permiso sobre la cohorte"}, 404: {"description": "Cohorte o alerta no encontrada"}}
READ = "risk.read"
REVIEW = "risk.review"


def alert_rows(cohort_id):
    owner = aliased(User)
    return (
        select(RiskAlert, Person.display_name, owner.display_name)
        .join(Enrollment, Enrollment.id == RiskAlert.enrollment_id)
        .join(Person, Person.id == Enrollment.person_id)
        .outerjoin(owner, owner.id == RiskAlert.assigned_to)
        .where(Enrollment.cohort_id == cohort_id, Person.is_synthetic, RiskAlert.synthetic_only,
               RiskAlert.human_review_only, RiskAlert.validated_for_people.is_(False))
    )


def alert_out(alert, learner_name, assigned_to):
    return RiskAlertOut(
        id=alert.id, learner_name=learner_name, model_version=alert.model_version, cutoff=alert.cutoff,
        status=alert.status, experimental_support_signal=alert.experimental_support_signal,
        abstention_reason=alert.abstention_reason, unjustified_absence_days=alert.unjustified_absence_days,
        justified_absence_days=alert.justified_absence_days, attendance_unknown_fraction=alert.attendance_unknown_fraction,
        mean_competency_level=alert.mean_competency_level, review_state=alert.review_state, assigned_to=assigned_to,
    )


def load_alert(db, cohort_id, alert_id, lock=False):
    query = alert_rows(cohort_id).where(RiskAlert.id == alert_id)
    if lock:
        query = query.with_for_update(of=RiskAlert)
    row = db.execute(query).one_or_none()
    if row is None:
        raise UserFacingError(404, "risk_alert_not_found", "No encontramos esta alerta en la cohorte.")
    return row


@router.get("", response_model=RiskAlertList, responses=ERRORS, summary="Alertas sintéticas de una cohorte autorizada")
def list_risk_alerts(cohort_id: str, p: CurrentPrincipal, db: DB, state: ReviewState | None = None,
                     limit: int = Query(25, ge=1, le=100), offset: int = Query(0, ge=0)) -> RiskAlertList:
    require_cohort(db, p, READ, cohort_id)
    query = alert_rows(cohort_id)
    if state:
        query = query.where(RiskAlert.review_state == state)
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = db.execute(query.order_by(RiskAlert.cutoff.desc(), RiskAlert.id).offset(offset).limit(limit)).all()
    audit.record(db, p, "risk.alerts_viewed", "cohort", cohort_id, returned=len(rows))
    db.commit()
    return RiskAlertList(total=total, items=[alert_out(*row) for row in rows])


@router.get("/{alert_id}", response_model=AlertReviewOut, responses=ERRORS, summary="Evidencia e intervenciones de una alerta sintética")
def get_risk_alert(cohort_id: str, alert_id: uuid.UUID, p: CurrentPrincipal, db: DB) -> AlertReviewOut:
    require_cohort(db, p, READ, cohort_id)
    row = load_alert(db, cohort_id, alert_id)
    history = db.execute(
        select(Intervention, User.display_name).join(User, User.id == Intervention.actor_user_id)
        .where(Intervention.alert_id == alert_id).order_by(Intervention.occurred_at, Intervention.id)
    ).all()
    audit.record(db, p, "risk.alert_viewed", "risk_alert", str(alert_id))
    db.commit()
    return AlertReviewOut(alert=alert_out(*row), interventions=[
        InterventionOut(id=item.id, kind=item.kind, note=item.note, occurred_at=item.occurred_at, actor=name)
        for item, name in history
    ])


@router.post("/{alert_id}/interventions", status_code=201, response_model=RiskAlertOut,
             responses={**ERRORS, 409: {"description": "Alerta cerrada o estado de revisión desfasado"}},
             summary="Registrar intervención humana de apoyo o cerrar una alerta de revisión")
def record_intervention(cohort_id: str, alert_id: uuid.UUID, body: InterventionWrite,
                        p: CurrentPrincipal, db: DB) -> RiskAlertOut:
    require_cohort(db, p, REVIEW, cohort_id)
    alert, learner_name, owner_name = load_alert(db, cohort_id, alert_id, lock=True)
    if alert.review_state == "closed" or alert.review_state != body.expected_state:
        raise UserFacingError(409, "risk_review_changed", "La revisión ha cambiado. Actualiza la alerta antes de guardar.")
    previous = alert.review_state
    if alert.assigned_to is None:
        alert.assigned_to = p.user.id
        owner_name = p.user.display_name
    alert.review_state = "closed" if body.kind == "closure" else "in_review"
    db.add(Intervention(alert_id=alert.id, actor_user_id=p.user.id, kind=body.kind, note=body.note))
    audit.record(db, p, "risk.intervention_recorded", "risk_alert", str(alert.id),
                 kind=body.kind, previous_state=previous, review_state=alert.review_state)
    db.commit()
    return alert_out(alert, learner_name, owner_name)
