import uuid

from fastapi import APIRouter, HTTPException, Path, Response, status
from sqlalchemy import select

from app.core import audit
from app.core.deps import DB, CurrentPrincipal
from app.modules.admissions.models import Application
from app.modules.catalog.models import Call
from app.modules.identity.models import User
from app.modules.requirements.models import RequirementReview, RequirementReviewRevision
from app.modules.requirements.schemas import (
    REQUIREMENT_REF_PATTERN,
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
        items=[RequirementRevisionOut(revision=r.revision, result=r.result, reviewer=names.get(r.reviewer_user_id), reviewed_at=r.reviewed_at, reason=r.reason) for r in revisions],
    )
