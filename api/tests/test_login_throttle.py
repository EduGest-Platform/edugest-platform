"""Login brute-force protection: 429 with Retry-After after repeated failures; success clears the account counter."""

import pytest

from app.core import login_throttle
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


# ---------- Client IP behind a proxy (PR 97 follow-up, David + security review) ----------

@pytest.mark.parametrize(("hops", "peer", "header", "expected"), [
    (0, "10.0.0.1", "1.1.1.1, 9.9.9.9", "10.0.0.1"),          # local: the header is ignored
    (1, "10.0.0.1", "1.1.1.1, 9.9.9.9", "9.9.9.9"),           # Render: right-most entry, appended by the proxy
    (1, "10.0.0.1", "9.9.9.9", "9.9.9.9"),
    (1, "10.0.0.1", None, "10.0.0.1"),
    (2, "10.0.0.1", "spoofed, 8.8.8.8, 7.7.7.7", "8.8.8.8"),
    (2, "10.0.0.1", "7.7.7.7", "10.0.0.1"),                   # fewer entries than hops: never trust a client-written one
])
def test_client_ip_uses_the_entry_added_by_the_trusted_proxy(monkeypatch, hops, peer, header, expected):
    monkeypatch.setattr(settings, "trusted_proxy_hops", hops)
    assert login_throttle.client_ip(peer, header) == expected


def test_forged_left_entries_cannot_dodge_the_per_client_limit(client, monkeypatch):
    """Rotating a forged left-most X-Forwarded-For value must still count against the real (right-most) client."""
    monkeypatch.setattr(settings, "trusted_proxy_hops", 1)
    limit = settings.login_max_failures * 4
    for n in range(limit):
        email = f"nadie{n}@example.test"  # a different account each time, so only the per-client limit can trigger
        r = client.post("/api/v1/auth/login", json={"email": email, "password": "x"}, headers={"X-Forwarded-For": f"203.0.113.{n}, 198.51.100.7"})
        assert r.status_code == 401
    blocked = client.post("/api/v1/auth/login", json={"email": "otra@example.test", "password": "x"}, headers={"X-Forwarded-For": "203.0.113.250, 198.51.100.7"})
    assert blocked.status_code == 429


def test_a_forged_victim_ip_cannot_lock_out_the_victim(client, monkeypatch):
    monkeypatch.setattr(settings, "trusted_proxy_hops", 1)
    for n in range(settings.login_max_failures * 4):
        client.post("/api/v1/auth/login", json={"email": f"x{n}@example.test", "password": "x"}, headers={"X-Forwarded-For": "192.0.2.10, 198.51.100.66"})
    victim = client.post("/api/v1/auth/login", json={"email": DOCENTE, "password": settings.demo_password}, headers={"X-Forwarded-For": "192.0.2.10"})
    assert victim.status_code == 200  # the attacker's failures counted against 198.51.100.66, not against the forged 192.0.2.10


def test_several_forwarded_for_lines_use_the_last_one_added_by_the_proxy(client, monkeypatch):
    monkeypatch.setattr(settings, "trusted_proxy_hops", 1)
    for n in range(settings.login_max_failures * 4):
        client.post("/api/v1/auth/login", json={"email": f"y{n}@example.test", "password": "x"},
                    headers=[("X-Forwarded-For", f"203.0.113.{n}"), ("X-Forwarded-For", "198.51.100.9")])
    r = client.post("/api/v1/auth/login", json={"email": "z@example.test", "password": "x"},
                    headers=[("X-Forwarded-For", "203.0.113.99"), ("X-Forwarded-For", "198.51.100.9")])
    assert r.status_code == 429
