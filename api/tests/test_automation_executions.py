"""KAN-183: durable evaluation evidence, concurrent idempotency and rollback."""
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import func, inspect, select, text
from sqlalchemy.exc import DBAPIError

from app.core import audit
from app.core.db import engine
from app.main import app
from app.modules.admissions.models import Application, ApplicationEvent
from app.modules.audit.models import AuditEvent
from app.modules.automation.models import AutomationExecution
from app.modules.learning.models import Enrollment
from app.modules.identity.models import User
from app.modules.requirements.models import RequirementReview
from tests.conftest import ADMIN, API_DIR, ASPIRANTE, CAPT_DATA, CAPT_IA, CODER, COORD, DOCENTE, SEL_IA, login

CALL = "CONV-IA-2027A"
REF = "synthetic-v1"


@pytest.fixture
def setup_execution(client, db, monkeypatch):
    monkeypatch.setattr("app.modules.automation.service.utcnow", lambda: datetime(2026, 11, 19, 12, tzinfo=timezone.utc))
    admin = login(client, ADMIN)
    response = client.post(f"/api/v1/calls/{CALL}/requirements", headers=admin,
                           json={"ref": REF, "code": "synthetic", "label": "Synthetic definition", "kind": "required"})
    assert response.status_code == 201
    application = db.scalar(select(Application).where(Application.call_id == CALL))
    base = f"/api/v1/applications/{application.id}"
    return admin, application, base


def record(client, headers, base, **overrides):
    return client.post(base + "/automation-executions/requirement-prefilter", headers=headers,
                       json={"requirement_refs": [REF], **overrides})


def record_counts(db):
    db.expire_all()
    return (db.scalar(select(func.count()).select_from(AutomationExecution)),
            db.scalar(select(func.count()).select_from(AuditEvent).where(AuditEvent.action == "automation_execution.recorded")))


def review(client, admin, base, expected=None):
    payload = {"result": "met", "reason": "Private-synthetic-reason-not-in-execution"}
    if expected:
        payload["expected_version"] = expected
    r = client.put(base + f"/requirement-reviews/{REF}", headers=admin, json=payload)
    assert r.status_code in (200, 201)


def test_record_survives_new_session_and_retry_without_duplicates(client, db, setup_execution):
    admin, application, base = setup_execution
    stage = application.stage
    events = db.scalar(select(func.count()).select_from(ApplicationEvent))
    enrollments = db.scalar(select(func.count()).select_from(Enrollment))
    first = record(client, admin, base)
    assert first.status_code == 201, first.text
    body = first.json()
    assert body["outcome"] == "human_review" and body["snapshot"]["evaluation_only"]
    with TestClient(app) as another_client:
        retry = record(another_client, login(another_client, SEL_IA), base)
        assert retry.status_code == 200 and retry.json() == body
        listed = another_client.get(base + "/automation-executions", headers=admin)
        assert listed.status_code == 200 and listed.json()["items"] == [body]
    assert record_counts(db) == (1, 1)
    assert db.get(Application, application.id).stage == stage
    assert db.scalar(select(func.count()).select_from(ApplicationEvent)) == events
    assert db.scalar(select(func.count()).select_from(Enrollment)) == enrollments
    assert db.scalar(select(RequirementReview)) is None


def test_utc_day_deduplicates_retries_but_preserves_daily_reevaluation(client, db, setup_execution, monkeypatch):
    admin, _, base = setup_execution
    clock = [datetime(2026, 11, 19, 23, 50, tzinfo=timezone.utc)]
    monkeypatch.setattr("app.modules.automation.service.utcnow", lambda: clock[0])
    first = record(client, admin, base)
    assert first.status_code == 201
    # The local date changed, but the UTC day did not.
    clock[0] = datetime(2026, 11, 20, 1, 55, tzinfo=timezone(timedelta(hours=2)))
    same_day = record(client, admin, base)
    assert same_day.status_code == 200 and same_day.json() == first.json()
    clock[0] = datetime(2026, 11, 20, 0, 0, tzinfo=timezone.utc)
    next_day = record(client, admin, base)
    assert next_day.status_code == 201
    assert next_day.json()["id"] != first.json()["id"]
    assert next_day.json()["idempotency_key"] != first.json()["idempotency_key"]
    assert next_day.json()["snapshot"] == first.json()["snapshot"]
    assert next_day.json()["evaluated_at"] != first.json()["evaluated_at"]
    clock[0] = datetime(2026, 11, 19, 20, 2, tzinfo=timezone(timedelta(hours=-4)))
    assert record(client, admin, base).status_code == 200
    assert record_counts(db) == (2, 2)


def test_changed_review_versions_make_new_records_including_no_action(client, db, setup_execution):
    admin, _, base = setup_execution
    first = record(client, admin, base).json()
    review(client, admin, base)
    second = record(client, admin, base)
    assert second.status_code == 201 and second.json()["outcome"] == "no_action"
    review(client, admin, base, expected=1)  # same result, new human review version
    third = record(client, admin, base)
    assert third.status_code == 201 and third.json()["outcome"] == "no_action"
    assert len({first["idempotency_key"], second.json()["idempotency_key"], third.json()["idempotency_key"]}) == 3
    assert third.json()["snapshot"]["items"][0]["review_version"] == 2
    assert "Private-synthetic-reason" not in third.text
    listed = client.get(base + "/automation-executions?limit=1", headers=admin).json()
    assert listed["total"] == 3 and listed["limit"] == 1 and len(listed["items"]) == 1
    assert record_counts(db) == (3, 3)


def test_concurrent_retries_create_one_record_and_one_audit(client, db, setup_execution):
    admin, _, base = setup_execution

    def submit(_):
        with TestClient(app) as independent:
            response = record(independent, admin, base)
            return response.status_code, response.json()["id"]

    with ThreadPoolExecutor(max_workers=2) as pool:
        replies = list(pool.map(submit, range(2)))
    assert sorted(status for status, _ in replies) == [200, 201]
    assert len({execution_id for _, execution_id in replies}) == 1
    assert record_counts(db) == (1, 1)


def test_audit_failure_rolls_back_record_and_key(db, setup_execution, monkeypatch):
    admin, _, base = setup_execution

    def fail(*args, **kwargs):
        raise RuntimeError("Synthetic audit failure")

    monkeypatch.setattr(audit, "record", fail)
    with TestClient(app, raise_server_exceptions=False) as quiet:
        assert record(quiet, admin, base).status_code == 500
    assert record_counts(db) == (0, 0)
    monkeypatch.undo()
    with TestClient(app) as retry:
        assert record(retry, admin, base).status_code == 201


@pytest.mark.parametrize("who", [ADMIN, CAPT_IA, SEL_IA])
def test_allowed_writers(client, setup_execution, who):
    _, _, base = setup_execution
    assert record(client, login(client, who), base).status_code == 201


@pytest.mark.parametrize("who", [CAPT_DATA, COORD, DOCENTE, ASPIRANTE, CODER])
def test_denied_writers_leave_no_record_or_record_audit(client, db, setup_execution, who):
    _, _, base = setup_execution
    assert record(client, login(client, who), base).status_code == 403
    assert record_counts(db) == (0, 0)


@pytest.mark.parametrize("who", [CAPT_DATA, DOCENTE, ASPIRANTE, CODER])
def test_denied_readers_cannot_see_another_application_record(client, setup_execution, who):
    admin, _, base = setup_execution
    assert record(client, admin, base).status_code == 201
    assert client.get(base + "/automation-executions", headers=login(client, who)).status_code == 403


def test_coordination_reads_but_cannot_record(client, setup_execution):
    admin, _, base = setup_execution
    assert record(client, admin, base).status_code == 201
    assert client.get(base + "/automation-executions", headers=login(client, COORD)).status_code == 200


@pytest.mark.parametrize("extra", [{"idempotency_key": "forged"}, {"outcome": "no_action"}, {"evaluated_at": "2020-01-01"}, {"recorded_by": "forged"}])
def test_server_owned_fields_cannot_be_forged(client, db, setup_execution, extra):
    admin, _, base = setup_execution
    assert record(client, admin, base, **extra).status_code == 422
    assert record_counts(db) == (0, 0)


def test_invalid_and_anonymous_requests_leave_no_record(client, db, setup_execution):
    admin, _, base = setup_execution
    assert record(client, {}, base).status_code == 401
    assert client.get(base + "/automation-executions").status_code == 401
    assert record(client, admin, base, requirement_refs=[]).status_code == 422
    assert record(client, admin, base, requirement_refs=["unknown"]).status_code == 404
    assert record_counts(db) == (0, 0)


def test_database_record_updates_are_blocked_and_audit_has_no_snapshot(client, db, setup_execution):
    admin, _, base = setup_execution
    assert record(client, admin, base).status_code == 201
    event = db.scalar(select(AuditEvent).where(AuditEvent.action == "automation_execution.recorded"))
    assert set(event.meta) == {"execution_id", "kind", "rule_version", "outcome"}
    assert "Private-synthetic-reason" not in json.dumps(event.meta)
    with pytest.raises(DBAPIError):
        db.execute(text("UPDATE automation_execution SET outcome = 'no_action'"))
    db.rollback()


def test_application_deletion_cascades_to_execution_without_requiring_trigger_bypass(client, db, setup_execution):
    admin, application, base = setup_execution
    assert record(client, admin, base).status_code == 201
    assert record_counts(db) == (1, 1)
    db.execute(text("DELETE FROM application WHERE id = :id"), {"id": application.id})
    db.commit()
    assert db.scalar(select(AutomationExecution)) is None
    # Execution deletion does not silently erase independent audit history.
    assert record_counts(db) == (0, 1)


def test_legacy_snapshot_shape_remains_readable(client, db, setup_execution):
    admin, application, base = setup_execution
    old_shape = {"schema_version": 0, "selected_refs": [REF], "flags": {"needs_review": True}, "optional": None}
    row = AutomationExecution(application_id=application.id, call_id=application.call_id, kind="requirement_prefilter",
                              rule_version="prefilter-v0", idempotency_key="0" * 64, outcome="human_review",
                              stage_at_evaluation=application.stage, snapshot=old_shape,
                              recorded_by=db.scalar(select(User.id).where(User.email == ADMIN)))
    db.add(row)
    db.commit()
    result = client.get(base + "/automation-executions", headers=admin)
    assert result.status_code == 200, result.text
    assert result.json()["total"] == 1
    assert result.json()["items"][0]["snapshot"] == old_shape
    assert result.json()["items"][0]["rule_version"] == "prefilter-v0"


def test_migration_roundtrip_keeps_requirements_and_rag():
    cfg = Config(API_DIR + "/alembic.ini")
    cfg.set_main_option("script_location", API_DIR + "/alembic")
    try:
        command.downgrade(cfg, "0006")
        tables = set(inspect(engine).get_table_names())
        assert "automation_execution" not in tables
        assert {"call_requirement", "requirement_review", "knowledge_document", "knowledge_chunk"} <= tables
    finally:
        command.upgrade(cfg, "head")
    assert "automation_execution" in inspect(engine).get_table_names()
