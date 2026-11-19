"""Side-effect-free snapshot calculation shared by preview and execution recording."""
from datetime import timedelta
from hashlib import sha256

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import utcnow
from app.modules.admissions.models import Application
from app.modules.catalog.models import Call
from app.modules.automation.engine import Policy, Task, TaskKind, propose
from app.modules.requirements.models import CallRequirement, RequirementReview
from app.modules.requirements.schemas import PrefilterItem, PrefilterRequest, PrefilterResult

PREFILTER_RULE_VERSION = "prefilter-v1"


def calculate_prefilter(db: Session, application: Application, call: Call, body: PrefilterRequest) -> PrefilterResult:
    refs = sorted(body.requirement_refs)
    if len(set(refs)) != len(refs):
        raise HTTPException(422, "No repitas referencias")
    catalogue = list(db.scalars(select(CallRequirement).where(CallRequirement.call_id == call.id)))
    by_ref = {definition.ref: definition for definition in catalogue}
    if any(ref not in by_ref for ref in refs):
        raise HTTPException(404, "Requisito no configurado para esta convocatoria")
    selected = [by_ref[ref] for ref in refs]
    codes = {definition.code for definition in selected}
    if len(codes) != len(selected):
        raise HTTPException(422, "Selecciona una sola versión por código")
    unselected = sorted({definition.code for definition in catalogue} - codes)
    reviews = {review.requirement_ref: review for review in db.scalars(
        select(RequirementReview).where(RequirementReview.application_id == application.id, RequirementReview.requirement_ref.in_(refs))
    )}
    items, unresolved, advisory = [], [], []
    for definition in selected:
        review = reviews.get(definition.ref)
        verified = review is not None and review.requirement_definition_id == definition.id
        result = review.result if verified else "pending"
        items.append(PrefilterItem(ref=definition.ref, code=definition.code, definition_id=definition.id,
                                   definition_version=definition.version, kind=definition.kind, result=result, verified_review=verified,
                                   review_version=review.version if verified else None))
        if result not in {"met", "exception_approved"}:
            (unresolved if definition.kind == "required" else advisory).append(definition.ref)
    now = utcnow()
    selection_hash = sha256("\n".join(refs).encode()).hexdigest()
    # This explicit evaluation reuses the engine; it does not enable a scheduled call policy.
    missing = tuple(sorted([f"ref:{ref}" for ref in unresolved] + [f"unselected:{code}" for code in unselected]))
    proposals = propose([Task(call_id=call.id, application_id=str(application.id),
                              task_id=f"requirements:{selection_hash}", kind=TaskKind.REQUIREMENTS,
                              due_at=now, missing_requirements=missing)],
                        Policy(call_id=call.id, version=PREFILTER_RULE_VERSION, response_grace=timedelta(0), enabled=True), now)
    return PrefilterResult(application_id=application.id, call_id=call.id, items=items, unselected_codes=unselected,
                           unresolved_required_refs=unresolved, advisory_refs=advisory,
                           human_review_required=bool(proposals), proposed_action=proposals[0].action.value if proposals else None,
                           proposal_key=proposals[0].key if proposals else None)
