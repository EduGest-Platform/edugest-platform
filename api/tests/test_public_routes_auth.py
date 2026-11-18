"""KAN-110: public routes versus FastAPI authentication, and no user enumeration through login."""

import re

import pytest
from sqlalchemy import func, select

from app.core.config import settings
from app.main import app
from app.modules.admissions.models import ApplicationEvent
from app.modules.identity import router as identity_router
from app.modules.identity.models import AuthSession, RoleAssignment, User
from tests.conftest import ADMIN, DOCENTE, login, new_application
from tests.test_contract import PUBLIC

ANY_ID = "00000000-0000-0000-0000-000000000000"
INVALID_AUTHORIZATIONS = [None, "Bearer synthetic-invalid-token", "Basic c3ludGhldGljOnN5bnRoZXRpYw==", "Bearer"]


def revoked_session_header(client, db) -> dict[str, str]:
    headers = login(client, DOCENTE)
    assert client.post("/api/v1/auth/logout", headers=headers).status_code == 204
    return headers


def with_authorization(value: str | None) -> dict[str, str]:
    return {"Authorization": value} if value else {}


@pytest.mark.parametrize("authorization", INVALID_AUTHORIZATIONS)
def test_public_routes_work_with_no_or_unusable_credentials(client, db, authorization):
    headers = with_authorization(authorization)
    assert client.get("/health", headers=headers).status_code == 200
    assert client.get("/api/v1/calls", headers=headers).status_code == 200
    created = client.post("/api/v1/applications", json=new_application(email=f"public-{abs(hash(authorization))}@example.test"), headers=headers)
    assert created.status_code == 201
    author = db.scalar(select(ApplicationEvent.actor_user_id).where(ApplicationEvent.application_id == created.json()["id"]))
    assert author is None


def test_public_inscription_with_revoked_session_is_anonymous(client, db):
    headers = revoked_session_header(client, db)
    created = client.post("/api/v1/applications", json=new_application(email="revoked.session@example.test"), headers=headers)
    assert created.status_code == 201
    assert db.scalar(select(ApplicationEvent.actor_user_id).where(ApplicationEvent.application_id == created.json()["id"])) is None


def test_public_inscription_creates_no_account_and_no_role(client, db):
    users_before = db.scalar(select(func.count()).select_from(User))
    roles_before = db.scalar(select(func.count()).select_from(RoleAssignment))
    assert client.post("/api/v1/applications", json=new_application(email="sin.cuenta@example.test")).status_code == 201
    assert db.scalar(select(func.count()).select_from(User)) == users_before
    assert db.scalar(select(func.count()).select_from(RoleAssignment)) == roles_before
    attempt = client.post("/api/v1/auth/login", json={"email": "sin.cuenta@example.test", "password": "cualquiera"})
    assert attempt.status_code == 401


def non_public_operations() -> list[tuple[str, str]]:
    operations = []
    for path, methods in app.openapi()["paths"].items():
        for method in methods:
            if (path, method) not in PUBLIC:
                operations.append((method.upper(), re.sub(r"\{[^}]+\}", ANY_ID, path)))
    return operations


def test_the_non_public_operations_list_is_not_empty():
    assert len(non_public_operations()) >= 8


@pytest.mark.parametrize("authorization", INVALID_AUTHORIZATIONS)
def test_every_non_public_operation_answers_401_without_usable_credentials(client, authorization):
    for method, path in non_public_operations():
        response = client.request(method, path, json={} if method in {"POST", "PUT", "PATCH"} else None, headers=with_authorization(authorization))
        assert response.status_code == 401, f"{method} {path} answered {response.status_code}"


def test_revoked_session_is_rejected_everywhere(client, db):
    headers = revoked_session_header(client, db)
    for method, path in non_public_operations():
        response = client.request(method, path, json={} if method in {"POST", "PUT", "PATCH"} else None, headers=headers)
        assert response.status_code == 401, f"{method} {path} answered {response.status_code}"


def test_token_in_query_string_is_not_accepted(client):
    token = login(client, ADMIN)["Authorization"].removeprefix("Bearer ")
    assert client.get(f"/api/v1/auth/me?access_token={token}").status_code == 401


@pytest.fixture
def password_checks(monkeypatch):
    calls = []
    original = identity_router.verify_password

    def spy(password, stored):
        calls.append(stored)
        return original(password, stored)

    monkeypatch.setattr(identity_router, "verify_password", spy)
    return calls


@pytest.mark.parametrize("email", ["nadie@example.test", "no-es-un-correo", "   ", "x" * 200 + "@example.test"])
def test_failed_login_for_unknown_or_malformed_email_still_checks_a_password(client, password_checks, email):
    response = client.post("/api/v1/auth/login", json={"email": email, "password": "synthetic-wrong"})
    assert response.status_code == 401
    assert password_checks == [identity_router.DUMMY_PASSWORD_HASH]


def test_failed_login_for_inactive_account_still_checks_its_password_and_stays_generic(client, db, password_checks):
    user = db.scalar(select(User).where(User.email == DOCENTE))
    user.is_active = False
    db.commit()
    inactive = client.post("/api/v1/auth/login", json={"email": DOCENTE, "password": settings.demo_password})
    unknown = client.post("/api/v1/auth/login", json={"email": "nadie@example.test", "password": settings.demo_password})
    assert inactive.status_code == unknown.status_code == 401
    assert {**inactive.json(), "request_id": None} == {**unknown.json(), "request_id": None}
    assert len(password_checks) == 2


def test_successful_login_checks_the_password_once_and_creates_one_session(client, db, password_checks):
    sessions_before = db.scalar(select(func.count()).select_from(AuthSession))
    login(client, ADMIN)
    assert len(password_checks) == 1 and password_checks[0] != identity_router.DUMMY_PASSWORD_HASH
    assert db.scalar(select(func.count()).select_from(AuthSession)) == sessions_before + 1


def scrypt_cost(stored: str) -> tuple:
    """Everything that sets the cost of verifying a hash: algorithm, N, r, p and the salt and key lengths."""
    algo, n, r, p, salt, key = stored.split("$")
    return algo, n, r, p, len(salt), len(key)


def test_dummy_hash_costs_the_same_as_the_hashes_stored_for_real_accounts(db):
    stored = db.scalar(select(User.password_hash).where(User.email == ADMIN))
    assert scrypt_cost(identity_router.DUMMY_PASSWORD_HASH) == scrypt_cost(stored)


def test_wrong_password_for_a_real_account_checks_that_account_hash_not_the_dummy(client, db, password_checks):
    stored = db.scalar(select(User.password_hash).where(User.email == ADMIN))
    response = client.post("/api/v1/auth/login", json={"email": ADMIN, "password": "synthetic-wrong"})
    assert response.status_code == 401
    assert password_checks == [stored]
