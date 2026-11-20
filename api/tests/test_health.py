"""Health endpoint: database connectivity is reported without leaking driver details (KAN-85)."""

import logging

from sqlalchemy.exc import OperationalError

from app.core.db import get_db
from app.main import app


class UnreachableDatabase:
    """Session stand-in whose queries fail like a stopped PostgreSQL server."""

    def execute(self, *args, **kwargs):
        raise OperationalError("select 1", {}, Exception("connection refused to 10.0.0.9:5432 user=secret_user"))


def test_health_reports_database_ok(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok", "database": "ok"}


def test_health_returns_503_without_driver_details_when_database_is_down(client, caplog):
    app.dependency_overrides[get_db] = lambda: UnreachableDatabase()
    try:
        with caplog.at_level(logging.WARNING):
            r = client.get("/health")
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert r.status_code == 503
    assert r.json() == {"status": "degraded", "database": "unavailable"}
    for leaked in ("10.0.0.9", "secret_user", "connection refused"):
        assert leaked not in r.text
        assert leaked not in caplog.text
    assert "health check: database unavailable" in caplog.text
