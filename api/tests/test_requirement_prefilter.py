"""KAN-148: server-derived, scoped and explicitly versioned human-review proposals."""
import json

import pytest
from sqlalchemy import func, select

from app.modules.admissions.models import Application, ApplicationEvent
from app.modules.audit.models import AuditEvent
from app.modules.learning.models import Enrollment
from app.modules.requirements.models import RequirementReview, RequirementReviewRevision
from tests.conftest import ADMIN, ASPIRANTE, CAPT_DATA, CAPT_IA, CODER, COORD, DOCENTE, SEL_IA, login

CALL = "CONV-IA-2027A"


@pytest.fixture
def configured(client, db):
    admin = login(client, ADMIN)
    target = db.scalar(select(Application).where(Application.call_id == CALL))
    url = f"/api/v1/applications/{target.id}"
    for ref, kind in (("required-v1", "required"), ("advice-v1", "recommended")):
        response = client.post(f"/api/v1/calls/{CALL}/requirements", headers=admin,
                               json={"ref": ref, "code": ref.split("-")[0], "label": "Synthetic definition", "kind": kind})
        assert response.status_code == 201
    return admin, target, url


def evaluate(client, headers, url, refs=None, **extra):
    return client.post(url + "/requirement-prefilter", headers=headers,
                       json={"requirement_refs": refs if refs is not None else ["required-v1", "advice-v1"], **extra})


def save(client, admin, url, ref, result, version=None):
    body = {"result": result, "reason": "Sensitive-synthetic-note-not-for-prefilter"}
    if version:
        body["expected_version"] = version
    response = client.put(f"{url}/requirement-reviews/{ref}", headers=admin, json=body)
    assert response.status_code in (200, 201), response.text


def counts(db):
    db.expire_all()
    return tuple(db.scalar(select(func.count()).select_from(model)) for model in
                 (ApplicationEvent, Enrollment, RequirementReview, RequirementReviewRevision))


def test_missing_required_is_human_review_and_retry_key_is_stable(client, db, configured):
    admin, target, url = configured
    before, stage = counts(db), target.stage
    first = evaluate(client, admin, url)
    assert first.status_code == 200, first.text
    result = first.json()
    assert result["unresolved_required_refs"] == ["required-v1"]
    assert result["advisory_refs"] == ["advice-v1"]
    assert result["human_review_required"] and result["proposed_action"] == "human_review"
    repeated = evaluate(client, admin, url, refs=["advice-v1", "required-v1"]).json()
    assert repeated["proposal_key"] == result["proposal_key"]
    assert result["evaluation_only"] and result["scope"] == "explicit_versions"
    assert counts(db) == before and db.get(Application, target.id).stage == stage


@pytest.mark.parametrize("result", ["met", "not_met", "exception_under_review", "exception_approved"])
def test_review_results_and_recommended_items_never_decide_admission(client, db, configured, result):
    admin, target, url = configured
    if result == "exception_approved":
        save(client, admin, url, "required-v1", "not_met")
        save(client, admin, url, "required-v1", "exception_under_review", 1)
        save(client, admin, url, "required-v1", result, 2)
    else:
        save(client, admin, url, "required-v1", result)
    before, stage = counts(db), target.stage
    response = evaluate(client, admin, url)
    body = response.json()
    assert body["human_review_required"] == (result in {"not_met", "exception_under_review"})
    assert body["advisory_refs"] == ["advice-v1"]  # never converted into an exclusion
    assert "Sensitive-synthetic-note" not in response.text
    assert "admitted" not in body and "eligible" not in body
    assert counts(db) == before and db.get(Application, target.id).stage == stage


def test_partial_selection_cannot_hide_an_unselected_code(client, configured):
    admin, _, url = configured
    result = evaluate(client, admin, url, refs=["advice-v1"]).json()
    assert result["unselected_codes"] == ["required"]
    assert result["human_review_required"] and result["proposed_action"] == "human_review"


def test_version_selection_is_explicit_not_latest_or_double_counted(client, configured):
    admin, _, url = configured
    save(client, admin, url, "required-v1", "met")
    published = client.post(f"/api/v1/calls/{CALL}/requirements", headers=admin,
                            json={"ref": "required-v2", "code": "required", "label": "Changed synthetic definition",
                                  "kind": "required", "expected_version": 1})
    assert published.status_code == 201
    assert not evaluate(client, admin, url).json()["human_review_required"]  # explicit v1 stays v1
    newer = evaluate(client, admin, url, refs=["required-v2", "advice-v1"]).json()
    assert newer["human_review_required"] and newer["items"][1]["definition_version"] == 2
    assert evaluate(client, admin, url, refs=["required-v1", "required-v2", "advice-v1"]).status_code == 422


def test_legacy_unbound_review_is_not_trusted(client, db, configured):
    admin, _, url = configured
    save(client, admin, url, "required-v1", "met")
    review = db.scalar(select(RequirementReview))
    review.requirement_definition_id = None
    db.commit()
    result = evaluate(client, admin, url).json()
    assert result["unresolved_required_refs"] == ["required-v1"]
    assert not next(item for item in result["items"] if item["ref"] == "required-v1")["verified_review"]


@pytest.mark.parametrize("who", [ADMIN, CAPT_IA, SEL_IA, COORD])
def test_authorized_readers_can_evaluate_in_scope(client, configured, who):
    _, _, url = configured
    assert evaluate(client, login(client, who), url).status_code == 200


@pytest.mark.parametrize("who", [CAPT_DATA, DOCENTE, ASPIRANTE, CODER])
def test_denied_users_leave_no_evaluation_audit(client, db, configured, who):
    _, _, url = configured
    assert evaluate(client, login(client, who), url).status_code == 403
    assert db.scalar(select(AuditEvent).where(AuditEvent.action == "requirement_prefilter.evaluated")) is None


def test_invalid_missing_foreign_and_forged_selections_do_not_write_audit(client, db, configured):
    admin, _, url = configured
    assert evaluate(client, {}, url).status_code == 401
    assert evaluate(client, admin, url, refs=[]).status_code == 422
    assert evaluate(client, admin, url, refs=["required-v1", "required-v1"]).status_code == 422
    assert evaluate(client, admin, url, missing_requirements=[]).status_code == 422
    assert evaluate(client, admin, url, refs=["unknown"]).status_code == 404
    other = client.post("/api/v1/calls/CONV-DATA-2027A/requirements", headers=admin,
                        json={"ref": "foreign", "code": "foreign", "label": "Synthetic", "kind": "required"})
    assert other.status_code == 201
    assert evaluate(client, admin, url, refs=["foreign"]).status_code == 404
    assert db.scalar(select(AuditEvent).where(AuditEvent.action == "requirement_prefilter.evaluated")) is None


def test_audit_has_ids_and_counts_without_free_text(client, db, configured):
    admin, _, url = configured
    save(client, admin, url, "required-v1", "not_met")
    assert evaluate(client, admin, url).status_code == 200
    event = db.scalar(select(AuditEvent).where(AuditEvent.action == "requirement_prefilter.evaluated"))
    assert set(event.meta) == {"definition_ids", "unresolved_required_count", "advisory_count", "unselected_code_count"}
    assert "Sensitive-synthetic-note" not in json.dumps(event.meta)
