from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app import models  # noqa: F401  (registers metadata)
from app.core.config import settings
from app.core.deps import DB
from app.modules.admissions.router import router as admissions_router
from app.modules.audit.router import router as audit_router
from app.modules.catalog.router import router as catalog_router
from app.modules.identity.router import router as identity_router

app = FastAPI(
    title="Gistar API (nombre provisional)",
    version="0.1.0",
    description=(
        "API del Proyecto Final 2 · Fundación Somos F5. **Datos exclusivamente sintéticos.** "
        "La autorización se comprueba en el servidor por rol y ámbito (programa, convocatoria o cohorte). "
        "La plataforma no toma decisiones automáticas de admisión, exclusión ni baja."
    ),
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)

API = "/api/v1"
for r in (identity_router, catalog_router, admissions_router, audit_router):
    app.include_router(r, prefix=API)


@app.get("/health", tags=["ops"], summary="Estado del servicio y de la base de datos")
def health(db: DB) -> dict:
    db.execute(text("select 1"))
    return {"status": "ok", "database": "ok"}
