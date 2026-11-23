"""Health endpoint: database connectivity is reported without leaking driver details (KAN-85)."""

import logging
import threading
import time

from sqlalchemy.exc import OperationalError

from app import main


def fail_like_stopped_database() -> None:
    """Probe stand-in that fails like a stopped PostgreSQL server."""
    raise OperationalError("select 1", {}, Exception("connection refused to 10.0.0.9:5432 user=secret_user"))


def test_health_reports_database_ok(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok", "database": "ok"}


def test_health_returns_503_without_driver_details_when_database_is_down(client, caplog, monkeypatch):
    monkeypatch.setattr(main, "check_database", fail_like_stopped_database)
    with caplog.at_level(logging.WARNING):
        r = client.get("/health")

    assert r.status_code == 503
    assert r.json() == {"status": "degraded", "database": "unavailable"}
    for leaked in ("10.0.0.9", "secret_user", "connection refused"):
        assert leaked not in r.text
        assert leaked not in caplog.text
    assert "health check: database unavailable" in caplog.text


def test_health_returns_503_within_deadline_when_probe_hangs(client, monkeypatch):
    """A pooled connection that stops answering must not hang /health past the probe deadline."""
    release_probe = threading.Event()
    monkeypatch.setattr(main, "check_database", lambda: release_probe.wait(5))
    monkeypatch.setattr(main, "HEALTH_PROBE_TIMEOUT_SECONDS", 0.2)
    try:
        started = time.monotonic()
        r = client.get("/health")
        elapsed = time.monotonic() - started
    finally:
        release_probe.set()

    assert r.status_code == 503
    assert r.json() == {"status": "degraded", "database": "unavailable"}
    assert elapsed < 2
