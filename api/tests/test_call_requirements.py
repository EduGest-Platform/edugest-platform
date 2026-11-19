"""KAN-135: immutable configuration, versioning and verified per-call review references."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError

from app.core import audit
from app.main import app

from app.modules.admissions.models import Application
from app.modules.audit.models import AuditEvent
from app.modules.requirements.models import CallRequirement, RequirementReview
from tests.conftest import ADMIN, ASPIRANTE, CAPT_DATA, CAPT_IA, CODER, COORD, DOCENTE, SEL_IA, login

CALL = "CONV-IA-2027A"
DATA = "CONV-DATA-2027A"


def publish(client, headers, call=CALL, **overrides):
    body = {"ref": "document-v1", "code": "document", "label": "Synthetic requirement", "kind": "required", "funder": "Synthetic funder"}
    return client.post(f"/api/v1/calls/{call}/requirements", json={**body, **overrides}, headers=headers)


def test_publish_read_and_version_without_reinterpreting_old_reviews(client, db):
    admin = login(client, ADMIN)
    original = publish(client, admin)
    assert original.status_code == 201, original.text
    first = original.json()
    target = db.scalar(select(Application).where(Application.call_id == CALL))
    stage = target.stage
    url = f"/api/v1/applications/{target.id}/requirement-reviews/document-v1"
    saved = client.put(url, headers=login(client, CAPT_IA), json={"result": "met", "reason": "Synthetic evidence"})
    assert saved.status_code == 201 and saved.json()["requirement_definition_id"] == first["id"]
    newer = publish(client, admin, ref="document-v2", kind="recommended", expected_version=1)
    assert newer.status_code == 201 and newer.json()["version"] == 2
    listed = client.get(f"/api/v1/calls/{CALL}/requirements", headers=login(client, SEL_IA))
    assert [d["kind"] for d in listed.json()["items"]] == ["required", "recommended"]
    db.expire_all()
    review = db.scalar(select(RequirementReview))
    assert str(review.requirement_definition_id) == first["id"]
    assert db.get(Application, target.id).stage == stage
    history = client.get(url + "/history", headers=admin).json()["items"]
    assert history[0]["requirement_definition_id"] == first["id"]
    event = db.scalar(select(AuditEvent).where(AuditEvent.action == "call_requirement.created"))
    assert set(event.meta) == {"definition_id", "version"}


@pytest.mark.parametrize("who", [CAPT_IA, CAPT_DATA, SEL_IA, COORD, DOCENTE, ASPIRANTE, CODER])
def test_configuration_denied_without_admin(client, db, who):
    assert publish(client, login(client, who)).status_code == 403
    assert db.scalar(select(CallRequirement)) is None


def test_anonymous_and_foreign_scope_cannot_read_or_configure(client):
    assert publish(client, {}).status_code == 401
    assert client.get(f"/api/v1/calls/{CALL}/requirements").status_code == 401
    assert client.get(f"/api/v1/calls/{CALL}/requirements", headers=login(client, CAPT_DATA)).status_code == 403


def test_unknown_or_foreign_requirement_rejected_without_writes(client, db):
    admin = login(client, ADMIN)
    assert publish(client, admin, call=DATA).status_code == 201
    target = db.scalar(select(Application).where(Application.call_id == CALL))
    for ref in ("document-v1", "missing"):
        r = client.put(f"/api/v1/applications/{target.id}/requirement-reviews/{ref}", headers=login(client, CAPT_IA),
                       json={"result": "met", "reason": "Synthetic evidence"})
        assert r.status_code == 404
    assert db.scalar(select(RequirementReview)) is None
    assert db.scalar(select(AuditEvent).where(AuditEvent.action == "requirement_review.created")) is None


def test_duplicate_and_stale_versions_are_conflicts(client):
    admin = login(client, ADMIN)
    assert publish(client, admin).status_code == 201
    assert publish(client, admin).status_code == 409
    assert publish(client, admin, ref="document-v2").status_code == 409
    assert publish(client, admin, expected_version=1).status_code == 409  # same ref cannot be reused
    assert publish(client, admin, ref="document-v2", expected_version=1).status_code == 201


@pytest.mark.parametrize("values", [{"label": " "}, {"kind": "mandatory"}, {"ref": "../unsafe"}, {"created_by": "forged"}, {"funder": " "}])
def test_invalid_and_spoofed_definitions_rejected(client, values):
    assert publish(client, login(client, ADMIN), **values).status_code == 422


def test_definitions_are_immutable_in_database(client, db):
    assert publish(client, login(client, ADMIN)).status_code == 201
    for statement in ("UPDATE call_requirement SET kind = 'recommended'", "DELETE FROM call_requirement"):
        with pytest.raises(DBAPIError):
            db.execute(text(statement))
        db.rollback()


def test_same_reference_in_two_calls_stays_call_scoped(client, db):
    admin = login(client, ADMIN)
    ia = publish(client, admin).json()
    other = publish(client, admin, call=DATA, kind="recommended").json()
    assert ia["id"] != other["id"]
    target = db.scalar(select(Application).where(Application.call_id == CALL))
    response = client.put(f"/api/v1/applications/{target.id}/requirement-reviews/document-v1", headers=admin,
                          json={"result": "met", "reason": "Synthetic evidence"})
    assert response.status_code == 201 and response.json()["requirement_definition_id"] == ia["id"]


def test_audit_failure_rolls_back_publication(db, monkeypatch):
    with TestClient(app, raise_server_exceptions=False) as client:
        admin = login(client, ADMIN)

        def fail(*args, **kwargs):
            raise RuntimeError("Synthetic audit failure")

        monkeypatch.setattr(audit, "record", fail)
        assert publish(client, admin).status_code == 500
    assert db.scalar(select(CallRequirement)) is None
