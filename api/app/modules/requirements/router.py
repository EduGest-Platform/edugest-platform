import uuid

from fastapi import APIRouter, HTTPException, Path, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.core import audit
from app.core.authz import Scope
from app.core.deps import DB, CurrentPrincipal
from app.modules.admissions.models import Application
from app.modules.catalog.models import Call
from app.modules.identity.models import User
from app.modules.requirements.models import CallRequirement, RequirementReview, RequirementReviewRevision
from app.modules.requirements.schemas import (
    REQUIREMENT_REF_PATTERN,
    CallRequirementList,
    CallRequirementOut,
    CallRequirementWrite,
    RequirementReviewHistory,
    RequirementReviewList,
    RequirementReviewOut,
    RequirementReviewWrite,
    RequirementRevisionOut,
)
from app.modules.requirements.service import require_access, save_review

router = APIRouter(tags=["requirements"])

RequirementRef = Path(pattern=REQUIREMENT_REF_PATTERN, description="Identificador del requisito dentro de la convocatoria")
_ERRORS = {403: {"description": "Sin permiso sobre el ámbito"}, 404: {"description": "Candidatura no encontrada"}}


def _load_application(db: DB, application_id: uuid.UUID) -> tuple[Application, Call]:
    row = db.execute(select(Application, Call).join(Call, Call.id == Application.call_id).where(Application.id == application_id)).first()
    if not row:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Candidatura no encontrada")
    return row[0], row[1]


def _reviewer_names(db: DB, user_ids: set[uuid.UUID | None]) -> dict[uuid.UUID, str]:
    ids = {i for i in user_ids if i}
    return {u.id: u.display_name for u in db.scalars(select(User).where(User.id.in_(ids)))} if ids else {}


def _out(review: RequirementReview, names: dict[uuid.UUID, str]) -> RequirementReviewOut:
    return RequirementReviewOut(
        id=review.id, application_id=review.application_id, requirement_ref=review.requirement_ref, result=review.result,
        reviewer=names.get(review.reviewer_user_id), reviewed_at=review.reviewed_at, reason=review.reason, version=review.version,
        requirement_definition_id=review.requirement_definition_id,
    )


@router.get(
    "/applications/{application_id}/requirement-reviews",
    response_model=RequirementReviewList,
    responses=_ERRORS,
    summary="Revisiones de requisitos de una candidatura (lista vacía = sin revisar, no «todo cumplido»)",
)
def list_requirement_reviews(application_id: uuid.UUID, p: CurrentPrincipal, db: DB) -> RequirementReviewList:
    a, call = _load_application(db, application_id)
    require_access(db, p, "requirements.read", call)
    reviews = list(db.scalars(select(RequirementReview).where(RequirementReview.application_id == a.id).order_by(RequirementReview.requirement_ref)))
    names = _reviewer_names(db, {r.reviewer_user_id for r in reviews})
    audit.record(db, p, "requirement_review.viewed", "application", str(a.id), codigo=a.codigo)
    db.commit()
    return RequirementReviewList(application_id=a.id, items=[_out(r, names) for r in reviews])


@router.put(
    "/applications/{application_id}/requirement-reviews/{requirement_ref}",
    response_model=RequirementReviewOut,
    responses={
        **_ERRORS,
        201: {"model": RequirementReviewOut, "description": "Primera revisión creada"},
        409: {"description": "Versión desfasada o cambio de resultado no permitido"},
    },
    summary="Registrar o revisar el resultado de un requisito, incluidas las excepciones. No cambia la etapa de la candidatura",
    description=(
        "`requirement_ref` debe existir en el catálogo de la convocatoria. Cada referencia identifica una definición "
        "inmutable; el resultado conserva su vínculo aunque se publiquen versiones nuevas. No incluir datos sensibles en `reason`."
    ),
)
def put_requirement_review(
    application_id: uuid.UUID, requirement_ref: str = RequirementRef, *, body: RequirementReviewWrite, response: Response, p: CurrentPrincipal, db: DB
) -> RequirementReviewOut:
    a, call = _load_application(db, application_id)
    review, created = save_review(db, p, a, call, requirement_ref, body)
    if created:
        response.status_code = status.HTTP_201_CREATED
    return _out(review, {p.user.id: p.user.display_name})


@router.get(
    "/applications/{application_id}/requirement-reviews/{requirement_ref}/history",
    response_model=RequirementReviewHistory,
    responses=_ERRORS,
    summary="Historial inmutable de una revisión: persona, resultado, fecha y motivo de cada versión",
)
def get_requirement_review_history(application_id: uuid.UUID, p: CurrentPrincipal, db: DB, requirement_ref: str = RequirementRef) -> RequirementReviewHistory:
    a, call = _load_application(db, application_id)
    require_access(db, p, "requirements.read", call)
    review = db.scalar(select(RequirementReview).where(RequirementReview.application_id == a.id, RequirementReview.requirement_ref == requirement_ref))
    if review is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Revisión no encontrada")
    revisions = list(db.scalars(select(RequirementReviewRevision).where(RequirementReviewRevision.review_id == review.id).order_by(RequirementReviewRevision.revision)))
    names = _reviewer_names(db, {r.reviewer_user_id for r in revisions})
    audit.record(db, p, "requirement_review.history_viewed", "application", str(a.id), codigo=a.codigo, requirement_ref=requirement_ref)
    db.commit()
    return RequirementReviewHistory(
        review_id=review.id,
        requirement_ref=review.requirement_ref,
        items=[RequirementRevisionOut(revision=r.revision, requirement_definition_id=r.requirement_definition_id,
                                      result=r.result, reviewer=names.get(r.reviewer_user_id), reviewed_at=r.reviewed_at, reason=r.reason) for r in revisions],
    )


def _load_call(db: DB, call_id: str) -> Call:
    call = db.get(Call, call_id)
    if call is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Convocatoria no encontrada")
    return call


@router.get("/calls/{call_id}/requirements", response_model=CallRequirementList,
            summary="Catálogo de requisitos y sus versiones inmutables dentro del ámbito autorizado")
def list_call_requirements(call_id: str, p: CurrentPrincipal, db: DB) -> CallRequirementList:
    call = _load_call(db, call_id)
    require_access(db, p, "requirements.read", call)
    definitions = db.scalars(select(CallRequirement).where(CallRequirement.call_id == call.id)
                             .order_by(CallRequirement.code, CallRequirement.version)).all()
    audit.record(db, p, "call_requirement.viewed", "call", call.id)
    db.commit()
    return CallRequirementList(call_id=call.id, items=[CallRequirementOut.model_validate(d) for d in definitions])


@router.post("/calls/{call_id}/requirements", response_model=CallRequirementOut, status_code=201,
             responses={403: {"description": "Solo administración"}, 409: {"description": "Referencia o versión en conflicto"}},
             summary="Publicar una definición inmutable; solo administración. Nunca decide admisión")
def create_call_requirement(call_id: str, body: CallRequirementWrite, p: CurrentPrincipal, db: DB) -> CallRequirementOut:
    call = _load_call(db, call_id)
    # No new role grants: only the existing admin wildcard can configure definitions.
    p.require("requirements.configure", Scope(program_id=call.program_id, call_id=call.id))
    db.execute(select(Call).where(Call.id == call.id).with_for_update()).scalar_one()
    previous = db.scalar(select(CallRequirement).where(CallRequirement.call_id == call.id, CallRequirement.code == body.code)
                         .order_by(CallRequirement.version.desc()).limit(1))
    version = previous.version if previous else 0
    if body.expected_version != version:
        raise HTTPException(status.HTTP_409_CONFLICT, "El catálogo ha cambiado: vuelve a cargar la versión")
    definition = CallRequirement(call_id=call.id, ref=body.ref, code=body.code, version=version + 1,
                                 label=body.label, kind=body.kind, funder=body.funder, created_by=p.user.id)
    db.add(definition)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Referencia o versión ya publicada") from exc
    audit.record(db, p, "call_requirement.created", "call", call.id, definition_id=str(definition.id), version=definition.version)
    db.commit()
    return CallRequirementOut.model_validate(definition)
