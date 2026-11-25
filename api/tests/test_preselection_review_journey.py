"""HTTP coverage for requirement reviews and the human handoff to selection."""

import pytest

from tests.conftest import CAPT_DATA, CAPT_IA, login, new_application
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
