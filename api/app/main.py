import logging
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as ProbeTimeout

from fastapi import FastAPI, Response, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app import models  # noqa: F401  (registers metadata)
from app.core.config import settings
from app.core.db import engine
from app.core.error_handling import REQUEST_ID_HEADER, install_error_handling
from app.modules.admissions.router import router as admissions_router
from app.modules.assistant.router import router as assistant_router
from app.modules.assistant_tools.router import router as assistant_tools_router
from app.modules.attendance.router import router as attendance_router
from app.modules.audit.router import router as audit_router
from app.modules.automation.router import router as automation_router
from app.modules.catalog.router import router as catalog_router
from app.modules.competencies.router import router as competencies_router
from app.modules.identity.router import router as identity_router
from app.modules.preselection.router import router as preselection_router
from app.modules.requirements.router import router as requirements_router
from app.modules.requirements.prefilter import router as prefilter_router
from app.modules.learning.team_router import router as teaching_team_router
from app.modules.learning.directory_router import router as academic_directory_router
from app.modules.selection.router import router as selection_router
from app.modules.submissions.router import router as submissions_router

app = FastAPI(
    title="EduGest API",
    version="0.1.0",
    description=(
        "API del Proyecto Final 2 · Fundación Somos F5. **Datos exclusivamente sintéticos.** "
        "La autorización se comprueba en el servidor por rol y ámbito (programa, convocatoria o cohorte). "
        "La plataforma no toma decisiones automáticas de admisión, exclusión ni baja."
    ),
)
install_error_handling(app)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
    expose_headers=[REQUEST_ID_HEADER],
)

API = "/api/v1"
for r in (
    identity_router,
    catalog_router,
    admissions_router,
    requirements_router,
    prefilter_router,
    preselection_router,
    selection_router,
    automation_router,
    attendance_router,
    competencies_router,
    submissions_router,
    assistant_router,
    assistant_tools_router,
    teaching_team_router,
    academic_directory_router,
    audit_router,
):
    app.include_router(r, prefix=API)


logger = logging.getLogger(__name__)

# Upper bound for the full /health database probe. Slightly above connect_timeout (5 s)
# so a refused new connection is still reported by the driver error, not by this deadline.
HEALTH_PROBE_TIMEOUT_SECONDS = 6

# Small dedicated pool: a probe stuck on a hung connection keeps its thread, but later
# probes queue behind it and still answer 503 when the deadline passes.
_health_probe_pool = ThreadPoolExecutor(max_workers=2, thread_name_prefix="health-probe")


def check_database() -> None:
    """Run ``select 1`` on a pooled connection; raises SQLAlchemyError if the database fails."""
    with engine.connect() as connection:
        connection.execute(text("select 1"))


HEALTH_UNAVAILABLE_RESPONSE = {
    "description": "La API responde pero no alcanza la base de datos",
    "content": {"application/json": {"example": {"status": "degraded", "database": "unavailable"}}},
}


@app.get(
    "/health",
    tags=["ops"],
    summary="Estado del servicio y de la base de datos",
    responses={status.HTTP_503_SERVICE_UNAVAILABLE: HEALTH_UNAVAILABLE_RESPONSE},
)
def health(response: Response) -> dict:
    """Return 200 when the database answers, 503 (without driver details) when it does not."""
    # The whole probe (pool checkout, pre-ping and select 1) is bounded by the deadline, so a
    # pooled connection to a database that stopped answering cannot hang the endpoint;
    # connect_timeout alone only bounds new connections.
    try:
        _health_probe_pool.submit(check_database).result(timeout=HEALTH_PROBE_TIMEOUT_SECONDS)
    except (SQLAlchemyError, ProbeTimeout):
        logger.warning("health check: database unavailable")
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "degraded", "database": "unavailable"}
    return {"status": "ok", "database": "ok"}
