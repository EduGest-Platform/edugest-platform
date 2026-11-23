"""Login brute-force protection: 429 with Retry-After after repeated failures; success clears the account counter."""

from app.core.config import settings
from tests.conftest import ADMIN, DOCENTE


def attempt(client, email, password="contraseña-incorrecta"):
    return client.post("/api/v1/auth/login", json={"email": email, "password": password})


def test_repeated_failures_lock_the_account_with_retry_after(client):
    for _ in range(settings.login_max_failures):
        assert attempt(client, DOCENTE).status_code == 401
    blocked = attempt(client, DOCENTE, settings.demo_password)  # even the right password waits
    assert blocked.status_code == 429
    assert int(blocked.headers["Retry-After"]) > 0
    assert blocked.json()["code"] == "too_many_login_attempts"


def test_lock_is_per_account(client):
    for _ in range(settings.login_max_failures):
        attempt(client, DOCENTE)
    assert attempt(client, ADMIN, settings.demo_password).status_code == 200


def test_success_before_the_limit_clears_the_counter(client):
    for _ in range(settings.login_max_failures - 1):
        attempt(client, DOCENTE)
    assert attempt(client, DOCENTE, settings.demo_password).status_code == 200
    for _ in range(settings.login_max_failures - 1):
        attempt(client, DOCENTE)
    assert attempt(client, DOCENTE, settings.demo_password).status_code == 200


def test_unknown_accounts_are_throttled_too(client):
    for _ in range(settings.login_max_failures):
        attempt(client, "nadie@example.test")
    assert attempt(client, "nadie@example.test").status_code == 429
