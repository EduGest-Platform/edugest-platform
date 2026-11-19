"""Record server-computed snapshots and their audit atomically, deduplicated by semantic input."""
import json
import uuid
from hashlib import sha256

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.core import audit
from app.core.authz import Principal
from app.core.db import utcnow
from app.modules.admissions.models import Application
from app.modules.automation.models import AutomationExecution
from app.modules.requirements.prefilter_service import PREFILTER_RULE_VERSION, calculate_prefilter
from app.modules.requirements.schemas import PrefilterRequest
from app.modules.requirements.service import load_application, require_access


def record_requirement_execution(db: Session, actor: Principal, application_id: uuid.UUID,
                                 body: PrefilterRequest) -> tuple[AutomationExecution, bool]:
    application, call = load_application(db, application_id)
    require_access(db, actor, "requirements.review", call)
    # Serializes simultaneous records for this application, including the no-action case.
    application = db.scalar(select(Application).where(Application.id == application.id)
                             .with_for_update().execution_options(populate_existing=True))
    snapshot = calculate_prefilter(db, application, call, body).model_dump(mode="json")
    payload = {"rule_version": PREFILTER_RULE_VERSION, "stage": application.stage, "snapshot": snapshot}
    key = sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    outcome = "human_review" if snapshot["human_review_required"] else "no_action"
    statement = insert(AutomationExecution).values(
        id=uuid.uuid4(), application_id=application.id, call_id=call.id, kind="requirement_prefilter",
        rule_version=PREFILTER_RULE_VERSION, idempotency_key=key, outcome=outcome,
        stage_at_evaluation=application.stage, snapshot=snapshot, recorded_by=actor.user.id, evaluated_at=utcnow(),
    ).on_conflict_do_nothing(index_elements=[AutomationExecution.idempotency_key]).returning(AutomationExecution.id)
    created_id = db.scalar(statement)
    execution = db.scalar(select(AutomationExecution).where(AutomationExecution.idempotency_key == key))
    if created_id is not None:
        audit.record(db, actor, "automation_execution.recorded", "application", str(application.id),
                     execution_id=str(execution.id), kind=execution.kind, rule_version=execution.rule_version, outcome=outcome)
    db.commit()
    return execution, created_id is not None
