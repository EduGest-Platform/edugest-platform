"""Evaluate explicit requirement versions; never infer eligibility or change admission state."""
import uuid
from datetime import timedelta
from hashlib import sha256
from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select

from app.core import audit
from app.core.db import utcnow
from app.core.deps import CurrentPrincipal, DB
from app.modules.automation.engine import Policy, Task, TaskKind, propose
from app.modules.requirements.models import CallRequirement, RequirementReview
from app.modules.requirements.router import _load_application
from app.modules.requirements.schemas import REQUIREMENT_REF_PATTERN, ReviewResult
from app.modules.requirements.service import require_access

router = APIRouter(tags=["requirements"])
Reference = Annotated[str, Field(pattern=REQUIREMENT_REF_PATTERN)]


class PrefilterRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    requirement_refs: list[Reference] = Field(min_length=1, max_length=100)


class PrefilterItem(BaseModel):
    ref: str
    code: str
    definition_id: uuid.UUID
    definition_version: int
    kind: Literal["required", "recommended"]
    result: ReviewResult
    verified_review: bool


class PrefilterResult(BaseModel):
    application_id: uuid.UUID
    call_id: str
    evaluation_only: Literal[True] = True
    scope: Literal["explicit_versions"] = "explicit_versions"
    items: list[PrefilterItem]
    unselected_codes: list[str]
    unresolved_required_refs: list[str]
    advisory_refs: list[str]
    human_review_required: bool
    proposed_action: Literal["human_review"] | None
    proposal_key: tuple[str, ...] | None


@router.post(
    "/applications/{application_id}/requirement-prefilter",
    response_model=PrefilterResult,
    responses={403: {"description": "Sin permiso o fuera de ámbito"},
               404: {"description": "Candidatura o requisito no encontrado en su convocatoria"},
               422: {"description": "Selección vacía, duplicada o con varias versiones de un código"}},
    summary="Evaluar requisitos seleccionados y proponer revisión humana, nunca decidir admisión",
    description="Selección explícita de versiones, no catálogo activo. Códigos omitidos exigen revisión humana. No escribe tareas ni cambia etapas.",
)
def evaluate_prefilter(application_id: uuid.UUID, body: PrefilterRequest, p: CurrentPrincipal, db: DB) -> PrefilterResult:
    application, call = _load_application(db, application_id)
    require_access(db, p, "requirements.read", call)
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
                                   definition_version=definition.version, kind=definition.kind, result=result, verified_review=verified))
        if result not in {"met", "exception_approved"}:
            (unresolved if definition.kind == "required" else advisory).append(definition.ref)
    now = utcnow()
    selection_hash = sha256("\n".join(refs).encode()).hexdigest()
    # This explicit evaluation reuses the engine; it does not enable a scheduled call policy.
    missing = tuple(sorted([f"ref:{ref}" for ref in unresolved] + [f"unselected:{code}" for code in unselected]))
    proposals = propose([Task(call_id=call.id, application_id=str(application.id),
                              task_id=f"requirements:{selection_hash}", kind=TaskKind.REQUIREMENTS,
                              due_at=now, missing_requirements=missing)],
                        Policy(call_id=call.id, version="prefilter-v1", response_grace=timedelta(0), enabled=True), now)
    audit.record(db, p, "requirement_prefilter.evaluated", "application", str(application.id),
                 definition_ids=[str(definition.id) for definition in selected],
                 unresolved_required_count=len(unresolved), advisory_count=len(advisory), unselected_code_count=len(unselected))
    db.commit()
    return PrefilterResult(application_id=application.id, call_id=call.id, items=items, unselected_codes=unselected,
                           unresolved_required_refs=unresolved, advisory_refs=advisory,
                           human_review_required=bool(proposals), proposed_action=proposals[0].action.value if proposals else None,
                           proposal_key=proposals[0].key if proposals else None)
