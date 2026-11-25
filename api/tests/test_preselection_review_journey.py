"""HTTP coverage for requirement reviews and the human handoff to selection."""

import pytest

from sqlalchemy import select

from app.modules.audit.models import AuditEvent
from app.modules.identity.models import User
from tests.conftest import ADMIN, CAPT_DATA, CAPT_IA, SEL_IA, login, new_application
from tests.test_admission_outcome_journeys import invite, mutation_snapshot, request

IA_CALL = "CONV-IA-2027A"
DATA_CALL = "CONV-DATA-2027A"


@pytest.mark.parametrize(
    ("call_id", "owner_email", "other_email"),
    [(IA_CALL, CAPT_IA, CAPT_DATA), (DATA_CALL, CAPT_DATA, CAPT_IA)],
)
def test_only_the_calls_staff_can_advance_an_application(client, db, call_id, owner_email, other_email):
    receipt = request(client, "POST", "/applications", body=new_application(call_id=call_id), expected=201)
    path = f"/applications/{receipt['id']}"
    owner = login(client, owner_email)
    outsider = login(client, other_email)
    payload = {"decision": "convocada", "reason": "Synthetic call to selection"}
    before = mutation_snapshot(db, receipt)

    request(client, "POST", f"{path}/preselection-decisions", outsider, payload, expected=403)
    assert mutation_snapshot(db, receipt) == before

    invitation = invite(client, path, owner)
    after = mutation_snapshot(db, receipt)
    request(client, "POST", f"{path}/preselection-decisions", outsider, payload, expected=403)
    request(client, "POST", f"{path}/preselection-decisions", owner, payload, expected=409)
    assert mutation_snapshot(db, receipt) == after
    assert request(client, "GET", f"{path}/preselection-decisions", owner)["items"] == [invitation]


@pytest.fixture
def required_document(client):
    admin = login(client, ADMIN)
    definition = request(client, "POST", f"/calls/{IA_CALL}/requirements", admin, {
        "ref": "synthetic-document-v1",
        "code": "synthetic-document",
        "label": "Synthetic document",
        "kind": "required",
    }, expected=201)
    receipt = request(client, "POST", "/applications", body=new_application(), expected=201)
    return definition, receipt, f"/applications/{receipt['id']}"


def test_exception_revisions_keep_actor_and_reason_in_scoped_history(client, db, required_document):
    definition, receipt, path = required_document
    review_path = f"{path}/requirement-reviews/{definition['ref']}"
    recruiter = login(client, CAPT_IA)
    selector = login(client, SEL_IA)
    outsider = login(client, CAPT_DATA)
    before = mutation_snapshot(db, receipt)
    opened = request(client, "PUT", review_path, recruiter, {
        "result": "exception_under_review",
        "reason": "Synthetic supporting note for review",
    }, expected=201)
    approval = {"result": "exception_approved", "reason": "Synthetic alternative evidence accepted", "expected_version": 1}
    request(client, "PUT", review_path, outsider, approval, expected=403)
    approved = request(client, "PUT", review_path, selector, approval)
    request(client, "PUT", review_path, selector, {
        "result": "not_met",
        "reason": "Synthetic stale amendment",
        "expected_version": 1,
    }, expected=409)

    request(client, "GET", f"{review_path}/history", outsider, expected=403)
    history = request(client, "GET", f"{review_path}/history", selector)["items"]
    assert [entry["revision"] for entry in history] == [1, 2]
    fields = ("result", "reviewer", "reason", "reviewed_at", "requirement_definition_id")
    for revision, saved in zip(history, (opened, approved), strict=True):
        assert {field: revision[field] for field in fields} == {field: saved[field] for field in fields}
    assert opened["reviewer"] != approved["reviewer"]
    assert mutation_snapshot(db, receipt) == before

    audit = db.scalars(select(AuditEvent).where(
        AuditEvent.target_id == receipt["id"],
        AuditEvent.action.in_(["requirement_review.created", "requirement_review.revised"]),
    ).order_by(AuditEvent.id)).all()
    assert [(row.action, row.meta["revision"], row.meta["result"]) for row in audit] == [
        ("requirement_review.created", 1, "exception_under_review"),
        ("requirement_review.revised", 2, "exception_approved"),
    ]
    for event, email in zip(audit, (CAPT_IA, SEL_IA), strict=True):
        assert db.get(User, event.actor_user_id).email == email
        assert set(event.meta) == {"codigo", "requirement_ref", "result", "from_result", "revision"}


def test_open_requirement_can_be_reviewed_after_the_human_handoff(client, db, required_document):
    definition, receipt, path = required_document
    recruiter = login(client, CAPT_IA)
    selector = login(client, SEL_IA)
    prefilter_path = f"{path}/requirement-prefilter"
    refs = {"requirement_refs": [definition["ref"]]}
    review_path = f"{path}/requirement-reviews/{definition['ref']}"
    initial = mutation_snapshot(db, receipt)

    first = request(client, "POST", prefilter_path, recruiter, refs)
    assert first["evaluation_only"] is True
    assert first["human_review_required"] is True
    assert first["unresolved_required_refs"] == [definition["ref"]]
    request(client, "PUT", review_path, recruiter, {
        "result": "exception_under_review",
        "reason": "Synthetic alternative evidence needs review",
    }, expected=201)
    assert mutation_snapshot(db, receipt) == initial

    invitation = invite(client, path, recruiter)
    assert invitation["evidence"]["unresolved_requirement_reviews"] == 1
    after_handoff = mutation_snapshot(db, receipt)
    request(client, "PUT", review_path, selector, {
        "result": "exception_approved",
        "reason": "Synthetic alternative evidence accepted after handoff",
        "expected_version": 1,
    })
    resolved = request(client, "POST", prefilter_path, selector, refs)
    assert resolved["human_review_required"] is False
    assert resolved["unresolved_required_refs"] == []
    assert resolved["items"][0]["review_version"] == 2
    assert request(client, "GET", f"{path}/preselection-decisions", selector)["items"] == [invitation]
    assert mutation_snapshot(db, receipt) == after_handoff
    assert after_handoff[0] == "convocada"
    assert not after_handoff[1] and not after_handoff[2]
