"""Owner-only repository evidence, with an optional public metadata lookup."""

import uuid
from typing import Annotated, Literal
from urllib.parse import urlsplit

from fastapi import APIRouter, Response
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import select

from app.core import audit
from app.core.config import settings
from app.core.db import utcnow
from app.core.deps import DB, CurrentPrincipal
from app.core.errors import UserFacingError
from app.modules.integrations.github.client import GithubError, GithubNotFound, GithubRateLimited, GithubReadOnlyClient
from app.modules.integrations.github.urls import parse_github_url
from app.modules.learning.models import Enrollment, PortfolioLink

router = APIRouter(prefix="/me/enrollments/{enrollment_id}/portfolio", tags=["portfolio"])
_ERRORS = {404: {"description": "Matrícula propia no encontrada"}}

class PortfolioWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    url: Annotated[str, Field(min_length=1, max_length=320)]
    authorized: Literal[True]

    @field_validator("url")
    @classmethod
    def canonical_repository(cls, value: str) -> str:
        raw = value.strip()
        try:
            parts = urlsplit(raw)
            if parts.scheme != "https" or parts.query or parts.fragment or any(ch.isspace() for ch in raw):
                raise ValueError
            target = parse_github_url(raw)
            if target.repo is None or len(parts.path.strip("/").split("/")) != 2 or ".." in target.repo:
                raise ValueError
        except ValueError:
            raise ValueError("Introduce la URL HTTPS de un repositorio GitHub, sin parámetros ni subrutas.") from None
        return f"https://github.com/{target.owner.lower()}/{target.repo.lower()}"


class PortfolioOut(BaseModel):
    url: str | None = None
    updated_at: AwareDatetime | None = None
    can_edit: bool
    can_lookup: bool


class PublicRepository(BaseModel):
    primary_language: Annotated[str, Field(max_length=100)] | None = None
    last_push_at: AwareDatetime | None = None


def own_enrollment(db: DB, actor: CurrentPrincipal, enrollment_id: uuid.UUID, *, lock: bool = False) -> Enrollment:
    if actor.user.person_id is not None:
        query = select(Enrollment).where(
            Enrollment.id == enrollment_id, Enrollment.person_id == actor.user.person_id,
        )
        enrollment = db.scalar(query.with_for_update() if lock else query)
        if enrollment is not None:
            return enrollment
    raise UserFacingError(404, "enrollment_not_found", "No encontramos esta matrícula en tu cuenta.")


def portfolio_out(enrollment: Enrollment, link: PortfolioLink | None) -> PortfolioOut:
    active = enrollment.estado == "activa"
    return PortfolioOut(url=link.url if link else None, updated_at=link.updated_at if link else None, can_edit=active,
                        can_lookup=active and settings.portfolio_github_lookup and link is not None)


@router.get("", response_model=PortfolioOut, responses=_ERRORS, summary="Consultar el enlace de portfolio propio")
def read_portfolio(enrollment_id: uuid.UUID, p: CurrentPrincipal, db: DB) -> PortfolioOut:
    enrollment = own_enrollment(db, p, enrollment_id)
    return portfolio_out(enrollment, db.get(PortfolioLink, enrollment_id))


@router.put("", response_model=PortfolioOut, responses={**_ERRORS, 409: {"description": "Se requiere matrícula activa"}},
            summary="Guardar un enlace autorizado a un repositorio")
def write_portfolio(enrollment_id: uuid.UUID, body: PortfolioWrite, p: CurrentPrincipal, db: DB) -> PortfolioOut:
    enrollment = own_enrollment(db, p, enrollment_id, lock=True)
    if enrollment.estado != "activa":
        raise UserFacingError(409, "portfolio_enrollment_inactive", "Se requiere una matrícula activa para guardar un enlace.")
    link = db.get(PortfolioLink, enrollment_id)
    if link and link.url == body.url:
        return portfolio_out(enrollment, link)
    if link is None:
        link = PortfolioLink(enrollment_id=enrollment_id)
        db.add(link)
    link.url = body.url
    link.updated_at = utcnow()
    audit.record(db, p, "portfolio.link_saved", "enrollment", str(enrollment_id))
    view = portfolio_out(enrollment, link)
    db.commit()
    return view


@router.delete("", status_code=204, responses=_ERRORS, summary="Eliminar el enlace propio, incluso al finalizar la matrícula")
def delete_portfolio(enrollment_id: uuid.UUID, p: CurrentPrincipal, db: DB) -> Response:
    own_enrollment(db, p, enrollment_id, lock=True)
    link = db.get(PortfolioLink, enrollment_id)
    if link is not None:
        db.delete(link)
        audit.record(db, p, "portfolio.link_removed", "enrollment", str(enrollment_id))
        db.commit()
    return Response(status_code=204)


@router.post("/metadata", response_model=PublicRepository,
             responses={**_ERRORS, 409: {"description": "Consulta no habilitada o enlace no disponible"},
                        429: {"description": "Cuota de GitHub agotada"}, 502: {"description": "GitHub no disponible"}},
             summary="Consultar idioma y última actividad pública del repositorio guardado")
def lookup_metadata(enrollment_id: uuid.UUID, p: CurrentPrincipal, db: DB) -> PublicRepository:
    enrollment = own_enrollment(db, p, enrollment_id)
    link = db.get(PortfolioLink, enrollment_id)
    if not (settings.portfolio_github_lookup and enrollment.estado == "activa" and link):
        raise UserFacingError(409, "portfolio_lookup_unavailable", "La consulta de GitHub no está disponible para este enlace.")
    target = parse_github_url(link.url)
    # Release the connection before making the optional outbound call.
    db.rollback()
    try:
        payload = GithubReadOnlyClient(timeout=4).get_json(f"/repos/{target.owner}/{target.repo}")
        if not isinstance(payload, dict):
            raise ValueError
        if payload.get("private") is not False or payload.get("visibility", "public") != "public":
            raise GithubNotFound()
        return PublicRepository(primary_language=payload.get("language"), last_push_at=payload.get("pushed_at"))
    except GithubNotFound:
        raise UserFacingError(404, "portfolio_public_repository_missing", "No encontramos un repositorio público con ese enlace.") from None
    except GithubRateLimited:
        raise UserFacingError(429, "portfolio_github_rate_limit", "GitHub ha limitado las consultas. Vuelve a intentarlo más tarde.") from None
    except (GithubError, ValueError):
        raise UserFacingError(502, "portfolio_github_unavailable", "No se pudo consultar GitHub. El enlace guardado sigue disponible.") from None
