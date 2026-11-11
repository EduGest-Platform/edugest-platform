from datetime import timedelta

from sqlalchemy import select

from app.core.db import utcnow
from app.modules.identity.models import AuthSession
from tests.conftest import ADMIN, CAPT_IA, DOCENTE, login


def test_login_returns_scoped_roles(client):
    r = client.post("/api/v1/auth/login", json={"email": " Captacion.IA@gistar.example ", "password": "gistar-demo-2026"})
    assert r.status_code == 200
    me = r.json()["me"]
    assert me["roles"] == [{"role": "captacion", "scope_type": "program", "scope_id": "P-IA"}]
    assert "password" not in r.text and "hash" not in r.text


def test_bad_credentials_are_generic(client):
    a = client.post("/api/v1/auth/login", json={"email": ADMIN, "password": "x"})
    b = client.post("/api/v1/auth/login", json={"email": "nadie@example.test", "password": "x"})
    assert a.status_code == b.status_code == 401
    assert a.json() == b.json()


def test_me_requires_token(client):
    assert client.get("/api/v1/auth/me").status_code == 401
    assert client.get("/api/v1/auth/me", headers={"Authorization": "Bearer inventado"}).status_code == 401


def test_logout_revokes_only_current_session(client):
    s1 = login(client, DOCENTE)
    s2 = login(client, DOCENTE)
    assert client.post("/api/v1/auth/logout", headers=s1).status_code == 204
    assert client.get("/api/v1/auth/me", headers=s1).status_code == 401
    assert client.get("/api/v1/auth/me", headers=s2).status_code == 200


def test_expired_session_is_rejected(client, db):
    h = login(client, CAPT_IA)
    for s in db.scalars(select(AuthSession)):
        s.expires_at = utcnow() - timedelta(minutes=1)
    db.commit()
    assert client.get("/api/v1/auth/me", headers=h).status_code == 401
