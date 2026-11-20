"""Explicit staff simulations using the existing deterministic proposal engine."""
import json
import uuid
from datetime import timedelta, timezone
from hashlib import sha256

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.core import audit
from app.core.authz import Principal
from app.core.db import utcnow
from app.modules.admissions.models import Application
from app.modules.automation.engine import Policy, Task, TaskKind, propose
from app.modules.automation.models import SimulatedReminder
from app.modules.automation.schemas import ReminderSimulationRequest
from app.modules.requirements.service import load_application, require_access

RULE_VERSION = "staff-simulation-v1"
PRESELECTION_STAGES = {"enviada", "requisitos_en_revision"}


def simulate_reminder(db: Session, actor: Principal, application_id: uuid.UUID,
                      body: ReminderSimulationRequest) -> tuple[SimulatedReminder | None, bool]:
    application, call = load_application(db, application_id)
    require_access(db, actor, "applications.crm", call)
    application = db.scalar(select(Application).where(Application.id == application.id)
                            .with_for_update().execution_options(populate_existing=True))
    if application.stage not in PRESELECTION_STAGES:
        raise HTTPException(409, "La simulación solo está disponible en preselección")
    now = utcnow().astimezone(timezone.utc)
    due_at = body.due_at.astimezone(timezone.utc)
    task = Task(call.id, str(application.id), body.task_ref, TaskKind(body.kind), due_at)
    policy = Policy(call.id, RULE_VERSION, timedelta(0), enabled=True)
    proposals = propose([task], policy, now)
    if not proposals:
        audit.record(db, actor, "simulated_reminder.not_due", "application", str(application.id), kind=body.kind)
        db.commit()
        return None, False
    # A rescheduled synthetic task is a different simulation. Offsets for one instant are not.
    key_payload = [proposals[0].key, due_at.isoformat()]
    key = sha256(json.dumps(key_payload, separators=(",", ":")).encode()).hexdigest()
    created = db.scalar(insert(SimulatedReminder).values(
        id=uuid.uuid4(), application_id=application.id, call_id=call.id,
        task_ref=body.task_ref, kind=body.kind, due_at=due_at, rule_version=RULE_VERSION,
        idempotency_key=key, recorded_by=actor.user.id, simulated_at=now,
    ).on_conflict_do_nothing(index_elements=[SimulatedReminder.idempotency_key]).returning(SimulatedReminder.id))
    reminder = db.scalar(select(SimulatedReminder).where(SimulatedReminder.idempotency_key == key))
    if created is not None:
        audit.record(db, actor, "simulated_reminder.recorded", "application", str(application.id),
                     reminder_id=str(reminder.id), kind=body.kind, rule_version=RULE_VERSION)
    db.commit()
    return reminder, created is not None
