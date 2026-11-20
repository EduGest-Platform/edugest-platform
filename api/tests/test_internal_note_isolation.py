"""KAN-261: persisted internal canaries never appear in learner, public, audit or denied responses."""
import logging

import pytest
from sqlalchemy import select

from app.modules.admissions.models import Application
from app.modules.identity.models import User
from tests.conftest import ADMIN, ASPIRANTE, CAPT_DATA, CODER, login

CALL = "CONV-IA-2027A"
REF = "synthetic-private-v1"
CANARIES = ("Synthetic-Internal-CRM-Canary-261", "Synthetic-Review-V1-Canary-261",
            "Synthetic-Review-V2-Canary-261", "Synthetic-Decision-Canary-261")


@pytest.fixture
def private_case(client, db):
    def prepare(email):
        user = db.scalar(select(User).where(User.email == email))
        assert user.person_id is not None
        target = db.scalar(select(Application).where(Application.person_id == user.person_id, Application.call_id == CALL))
        if target is None:
            target = Application(codigo="IA27A-PRIVATE261", person_id=user.person_id, call_id=CALL, stage="enviada",
                                 motivacion="Synthetic privacy boundary fixture", disponibilidad="Flexible", acepta_datos_sinteticos=True)
            db.add(target)
        else:
            target.stage = "enviada"
        db.commit()
        admin = login(client, ADMIN)
        base = f"/api/v1/applications/{target.id}"
        note = client.post(base + "/events", headers=admin, json={"tipo": "nota", "resumen": CANARIES[0]})
        assert note.status_code == 201, note.text
        definition = client.post(f"/api/v1/calls/{CALL}/requirements", headers=admin,
                                 json={"ref": REF, "code": "synthetic-private", "label": "Synthetic privacy fixture", "kind": "required"})
        assert definition.status_code == 201, definition.text
        for version, result in ((1, "not_met"), (2, "met")):
            body = {"result": result, "reason": CANARIES[version]}
            if version == 2:
                body["expected_version"] = 1
            saved = client.put(base + f"/requirement-reviews/{REF}", headers=admin, json=body)
            assert saved.status_code == (201 if version == 1 else 200), saved.text
        decision = client.post(base + "/preselection-decisions", headers=admin,
                                json={"decision": "convocada", "reason": CANARIES[3]})
        assert decision.status_code == 201, decision.text
        return target, base, admin
    return prepare


def assert_no_canaries(text):
    assert not any(canary in text for canary in CANARIES), text


def protected_paths(base):
    return (base, base + "/requirement-reviews", base + f"/requirement-reviews/{REF}/history",
            base + "/preselection-decisions", base + "/automation-executions", "/api/v1/audit-events")


@pytest.mark.parametrize("email", [ASPIRANTE, CODER])
def test_own_application_exposes_stage_but_no_internal_history(client, db, private_case, email):
    target, base, _ = private_case(email)
    learner = login(client, email)
    response = client.get("/api/v1/me/applications", headers=learner)
    assert response.status_code == 200
    own = next(row for row in response.json() if row["id"] == str(target.id))
    assert own["stage"] == "convocada"
    assert set(own) == {"id", "codigo", "call_id", "call_nombre", "stage", "created_at", "updated_at"}
    assert_no_canaries(response.text)
    # Query strings cannot opt into staff-only fields on the self-service projection.
    expanded = client.get("/api/v1/me/applications?include=events&expand=history&fields=reason", headers=learner)
    assert expanded.status_code == 200 and expanded.json() == response.json()
    for url in ("/api/v1/auth/me", "/api/v1/calls"):
        safe = client.get(url, headers=learner)
        assert safe.status_code == 200
        assert_no_canaries(safe.text)
    for url in protected_paths(base):
        denied = client.get(url, headers=learner)
        assert denied.status_code == 403, url
        assert_no_canaries(denied.text)
    assert client.post(base + "/events", headers=learner,
                       json={"tipo": "nota", "resumen": "Synthetic denied learner write"}).status_code == 403


def test_allowed_staff_can_read_actual_canaries_but_audit_never_copies_them(client, private_case):
    target, base, admin = private_case(ASPIRANTE)
    # Positive controls prevent a false pass caused by never persisting the sensitive fixture.
    dossier = client.get(base, headers=admin)
    assert dossier.status_code == 200 and CANARIES[0] in dossier.text
    revisions = client.get(base + f"/requirement-reviews/{REF}/history", headers=admin)
    assert revisions.status_code == 200 and all(value in revisions.text for value in CANARIES[1:3])
    decisions = client.get(base + "/preselection-decisions", headers=admin)
    assert decisions.status_code == 200 and CANARIES[3] in decisions.text
    # Even an authorized dossier does not inline unrelated review/decision reasons.
    assert all(value not in dossier.text for value in CANARIES[1:])
    audit = client.get("/api/v1/audit-events", headers=admin,
                       params={"target_type": "application", "target_id": str(target.id), "limit": 500})
    assert audit.status_code == 200
    actions = {event["action"] for event in audit.json()}
    assert {"application.event_added", "requirement_review.created", "requirement_review.revised", "preselection.decided"} <= actions
    assert_no_canaries(audit.text)
    public = client.get("/api/v1/calls")
    assert public.status_code == 200
    assert_no_canaries(public.text)


def test_foreign_scope_and_anonymous_errors_do_not_leak_internal_history(client, private_case):
    _, base, _ = private_case(ASPIRANTE)
    outsider = login(client, CAPT_DATA)
    for url in protected_paths(base):
        denied = client.get(url, headers=outsider)
        assert denied.status_code == 403, url
        assert_no_canaries(denied.text)
        anonymous = client.get(url)
        assert anonymous.status_code == 401, url
        assert_no_canaries(anonymous.text)


def test_logging_excludes_actual_internal_payloads_on_success_validation_and_denial(client, private_case, caplog):
    with caplog.at_level(logging.INFO, logger="app.access"):
        _, base, admin = private_case(ASPIRANTE)
        assert client.get(base, headers=admin).status_code == 200
        learner = login(client, ASPIRANTE)
        assert client.get(base, headers=learner).status_code == 403
        invalid = client.post(base + "/events", headers=admin, json={"tipo": "nota", "resumen": [CANARIES[0]]})
        assert invalid.status_code == 422
        assert_no_canaries(invalid.text)
    records = [record for record in caplog.records if record.name == "app.access"]
    assert records and any("422" in record.getMessage() for record in records)
    assert_no_canaries("\n".join(record.getMessage() for record in records))
    assert all(record.exc_info is None for record in records)
