"""KAN-175: the internal reason of a non-admission never leaves the staff who may read it.

PO decision 2026-11-22: external non-admission communication is generic; detailed individual reasons are visible
only to authorised staff and never appear in public responses, e-mail or logs. No e-mail is sent today (KAN-50),
so this covers the other channels: API responses, the CRM history, the audit trail and the application logs.
"""

import json
import logging

import pytest
from sqlalchemy import select

from app.modules.admissions.models import ApplicationEvent
from app.modules.audit.models import AuditEvent
from tests.conftest import ADMIN, CAPT_IA, COORD, DOCENTE, SEL_IA, login
from tests.test_own_selection_outcome import create_applicant_account, own_outcome_path
from tests.test_selection_decisions import DATA_CALL, decide, history, make_application

FIRST_VOTE_REASON = "q7azurite93v8 m4orchid61k2"
SECOND_VOTE_REASON = "r9cobalt42j6 n8topaz75w3"
PRIVATE_REASONS = (FIRST_VOTE_REASON, SECOND_VOTE_REASON)
MIN_PRIVATE_FRAGMENT_LENGTH = 8


def normalized_text(text):
    return "".join(character for character in text.casefold() if character.isalnum())


def assert_no_private_reason(text, channel):
    normalized = normalized_text(text)
    for reason in PRIVATE_REASONS:
        marker = normalized_text(reason)
        for index in range(len(marker) - MIN_PRIVATE_FRAGMENT_LENGTH + 1):
            fragment = marker[index:index + MIN_PRIVATE_FRAGMENT_LENGTH]
            assert fragment not in normalized, f"{channel} exposes a private reason fragment"


@pytest.mark.parametrize("reason", PRIVATE_REASONS)
def test_privacy_assertion_detects_partial_disclosures(reason):
    words = reason.split()
    for leaked in (
        reason,
        reason[:8],
        reason[-8:],
        words[0][2:10],
        words[1].upper(),
        " / ".join(words[0]),
    ):
        with pytest.raises(AssertionError, match="private reason fragment"):
            assert_no_private_reason(json.dumps({"detail": leaked}), "synthetic mutation")
    assert_no_private_reason("No admitida. Consulta el resultado de tu candidatura.", "generic outcome")


def assert_applicant_views_hide_the_reasons(
    client, applicant, application_id, *, stage, outcome=None, decided_at=None,
):
    applications = client.get("/api/v1/me/applications", headers=applicant)
    assert applications.status_code == 200, applications.text
    assert_no_private_reason(applications.text, "own applications")
    (application,) = [row for row in applications.json() if row["id"] == str(application_id)]
    assert application["stage"] == stage
    assert set(application) == {"id", "codigo", "call_id", "call_nombre", "stage", "created_at", "updated_at"}

    path = own_outcome_path(application_id)
    response = client.get(path, headers=applicant)
    assert response.status_code == 200, response.text
    assert response.headers["cache-control"] == "no-store"
    assert_no_private_reason(response.text, path)
    assert response.json() == {
        "application_id": str(application_id),
        "stage": stage,
        "outcome": outcome,
        "decided_at": decided_at,
        "enrollment": None,
    }


def assert_rejected_without_the_reasons(response, status_code=403):
    assert response.status_code == status_code, response.text
    assert_no_private_reason(response.text, str(response.request.url))


def test_the_internal_reasons_of_a_non_admission_stay_with_authorised_staff(client, db, caplog):
    caplog.set_level(logging.DEBUG)
    application = make_application(db)
    applicant = login(client, create_applicant_account(db, application))
    selector, coordinator = login(client, SEL_IA), login(client, COORD)

    # Default quorum of two: the first vote stays pending until a second person agrees.
    first = decide(client, selector, application.id, "no_admitida", reason=FIRST_VOTE_REASON)
    assert first.status_code == 202, first.text
    assert_applicant_views_hide_the_reasons(client, applicant, application.id, stage="pendiente_decision_humana")

    final = decide(client, coordinator, application.id, "no_admitida", reason=SECOND_VOTE_REASON)
    assert final.status_code == 201, final.text
    assert final.json()["decision"] == "no_admitida"
    assert final.json()["occurred_at"]
    assert_applicant_views_hide_the_reasons(
        client, applicant, application.id, stage="no_admitida",
        outcome="no_admitida", decided_at=final.json()["occurred_at"],
    )

    # Positive control: both reasons were stored, and authorised staff can read them.
    authorised = history(client, selector, application.id)
    assert authorised.status_code == 200, authorised.text
    assert all(reason in authorised.text for reason in PRIVATE_REASONS)

    # The applicant and staff without selection permission cannot read the decision history.
    recruiter = login(client, CAPT_IA)
    for outsider in (applicant, recruiter, login(client, DOCENTE)):
        assert_rejected_without_the_reasons(history(client, outsider, application.id))
    assert_rejected_without_the_reasons(history(client, {}, application.id), 401)
    assert_rejected_without_the_reasons(client.get(f"/api/v1/applications/{application.id}", headers=applicant))

    # A rejected write does not echo the reason it received: no permission, already decided, invalid body.
    for author, reason, status_code in (
        (recruiter, FIRST_VOTE_REASON, 403),
        (selector, FIRST_VOTE_REASON, 409),
        (selector, FIRST_VOTE_REASON + "x" * 501, 422),
    ):
        rejected = decide(client, author, application.id, "no_admitida", reason=reason)
        assert_rejected_without_the_reasons(rejected, status_code)

    # Recruitment may open the dossier and its CRM history, which only carry fixed texts.
    dossier = client.get(f"/api/v1/applications/{application.id}", headers=recruiter)
    assert dossier.status_code == 200, dossier.text
    assert dossier.json()["events"]
    assert_no_private_reason(dossier.text, "the recruitment dossier")

    db.expire_all()
    crm = db.scalars(select(ApplicationEvent.resumen).where(ApplicationEvent.application_id == application.id)).all()
    audit_rows = db.execute(select(AuditEvent.action, AuditEvent.meta)).all()
    assert crm
    assert {"selection.approved", "selection.decided"} <= {action for action, _ in audit_rows}
    assert_no_private_reason(json.dumps(crm), "the CRM history")
    assert_no_private_reason(json.dumps([meta for _, meta in audit_rows]), "the audit trail")

    # Positive control: the access log was captured, so the absence of the reasons means something.
    assert any(record.name == "app.access" for record in caplog.records)
    assert_no_private_reason(caplog.text, "the log output")


def test_selection_staff_of_another_call_cannot_read_the_reason(client, db):
    application = make_application(db, call_id=DATA_CALL)
    admin, coordinator = login(client, ADMIN), login(client, COORD)
    other_call_selector = login(client, SEL_IA)
    vote = decide(client, admin, application.id, "no_admitida", reason=FIRST_VOTE_REASON)
    assert vote.status_code == 202, vote.text
    pending = history(client, admin, application.id)
    assert pending.status_code == 200, pending.text
    assert pending.json()["items"] == []
    assert FIRST_VOTE_REASON in pending.text
    assert_rejected_without_the_reasons(history(client, other_call_selector, application.id))
    assert_rejected_without_the_reasons(
        decide(client, other_call_selector, application.id, "no_admitida", reason=SECOND_VOTE_REASON)
    )

    final = decide(client, coordinator, application.id, "no_admitida", reason=SECOND_VOTE_REASON)
    assert final.status_code == 201, final.text
    assert final.json()["decision"] == "no_admitida"
    authorised = history(client, admin, application.id)
    assert authorised.status_code == 200, authorised.text
    assert len(authorised.json()["items"]) == 1
    assert authorised.json()["pending_votes"] == []
    assert all(reason in authorised.text for reason in PRIVATE_REASONS)
    assert_rejected_without_the_reasons(history(client, other_call_selector, application.id))
    assert_rejected_without_the_reasons(
        decide(client, other_call_selector, application.id, "no_admitida", reason=FIRST_VOTE_REASON)
    )
