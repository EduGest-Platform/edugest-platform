"""Tests run against a real PostgreSQL database (never SQLite) given by GISTAR_TEST_DATABASE_URL."""

import os

import pytest

TEST_URL = os.environ.get("GISTAR_TEST_DATABASE_URL")
if not TEST_URL:
    raise RuntimeError("Define GISTAR_TEST_DATABASE_URL (PostgreSQL de pruebas, se vacía en cada test)")
os.environ["GISTAR_DATABASE_URL"] = TEST_URL
os.environ.setdefault("GISTAR_SCRYPT_N", "1024")

from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.core.db import SessionLocal  # noqa: E402
from app.main import app  # noqa: E402
from app.seed import reset, seed  # noqa: E402

API_DIR = os.path.dirname(os.path.dirname(__file__))


@pytest.fixture(scope="session", autouse=True)
def _migrated():
    cfg = Config(os.path.join(API_DIR, "alembic.ini"))
    cfg.set_main_option("script_location", os.path.join(API_DIR, "alembic"))
    command.downgrade(cfg, "base")
    command.upgrade(cfg, "head")
    yield


@pytest.fixture(autouse=True)
def _fresh_data():
    with SessionLocal() as db:
        reset(db)
        seed(db)
    yield


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture
def db():
    with SessionLocal() as s:
        yield s


def login(client: TestClient, email: str, password: str | None = None) -> dict[str, str]:
    r = client.post("/api/v1/auth/login", json={"email": email, "password": password or settings.demo_password})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


ADMIN = "admin@gistar.example"
CAPT_IA = "captacion.ia@gistar.example"
CAPT_DATA = "captacion.data@gistar.example"
SEL_IA = "seleccion.ia@gistar.example"
DOCENTE = "docente@gistar.example"
COORD = "coordinacion@gistar.example"
ASPIRANTE = "aspirante-01@example.test"
CODER = "coder-01@example.test"


def new_application(**over) -> dict:
    body = {
        "call_id": "CONV-IA-2027A",
        "nombre": "Persona Sintética",
        "email": "nueva.persona@example.test",
        "motivacion": "Quiero formarme en IA aplicada con proyectos.",
        "disponibilidad": "Tarde",
        "acepta_datos_sinteticos": True,
    }
    body.update(over)
    return body
