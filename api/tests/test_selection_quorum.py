"""Melissa round 3 Q11: a selection decision needs two different people by default (configurable per call)."""

import pytest
from sqlalchemy import func, select

from app.modules.admissions.models import Application
from app.modules.audit.models import AuditEvent
from app.modules.catalog.models import Call
from app.modules.learning.models import Enrollment
from app.modules.selection.models import SelectionApproval, SelectionDecision
from tests.conftest import ADMIN, CAPT_IA, COORD, DOCENTE, SEL_IA, login
from tests.test_selection_decisions import IA_CALL, IA_COHORT, decide, history, make_application, make_cohort


@pytest.fixture
def ready(db):
    make_cohort(db)
    call = db.get(Call, IA_CALL)
    call.plazas = 999
    db.commit()
    return make_application(db, stage="evaluacion_en_curso")


def count(db, model, application):
    db.expire_all()
    return db.scalar(select(func.count()).select_from(model).where(model.application_id == application.id))


def test_default_quorum_is_two(db):
    assert db.get(Call, IA_CALL).selection_quorum == 2


def test_first_vote_waits_and_changes_nothing_but_the_stage(client, db, ready):
    r = decide(client, login(client, SEL_IA), ready.id)
    assert r.status_code == 202, r.text
    body = r.json()
    assert body["state"] == "pending" and body["quorum"] == 2 and len(body["votes"]) == 1
    assert body["stage"] == "pendiente_decision_humana"
    assert count(db, SelectionDecision, ready) == 0
    assert db.scalar(select(func.count()).select_from(Enrollment).where(Enrollment.application_id == ready.id)) == 0


def test_two_different_people_agreeing_apply_the_decision_and_enroll(client, db, ready):
    decide(client, login(client, SEL_IA), ready.id)
    r = decide(client, login(client, COORD), ready.id)
    assert r.status_code == 201, r.text
    assert r.json()["decision"] == "admitida" and r.json()["enrollment_id"]
    db.expire_all()
    assert db.get(Application, ready.id).stage == "admitida"
    votes = db.scalars(select(SelectionApproval).where(SelectionApproval.application_id == ready.id)).all()
    assert len(votes) == 2 and all(v.decision_id for v in votes)
    actions = list(db.scalars(select(AuditEvent.action).where(AuditEvent.target_id == str(ready.id))))
    assert actions.count("selection.approved") == 1 and actions.count("selection.decided") == 1


def test_the_same_person_cannot_vote_twice(client, ready):
    decide(client, login(client, SEL_IA), ready.id)
    r = decide(client, login(client, SEL_IA), ready.id)
    assert r.status_code == 409 and r.json()["code"] == "already_approved"


def test_disagreement_waits_until_two_people_agree(client, db, ready):
    decide(client, login(client, SEL_IA), ready.id, "admitida")
    split = decide(client, login(client, COORD), ready.id, "lista_espera")
    assert split.status_code == 202 and split.json()["state"] == "disagreement"
    settled = decide(client, login(client, ADMIN), ready.id, "lista_espera")
    assert settled.status_code == 201 and settled.json()["decision"] == "lista_espera"
    db.expire_all()
    votes = db.scalars(select(SelectionApproval).where(SelectionApproval.application_id == ready.id)).all()
    decision_id = settled.json()["id"]
    assert len(votes) == 3 and all(str(v.decision_id) == decision_id for v in votes)  # the outvoted vote is kept, linked, and closed
    assert {v.decision for v in votes} == {"admitida", "lista_espera"}


def test_an_outvoted_vote_never_counts_towards_a_later_promotion(client, db, ready):
    decide(client, login(client, SEL_IA), ready.id, "admitida")  # outvoted
    decide(client, login(client, COORD), ready.id, "lista_espera")
    decide(client, login(client, ADMIN), ready.id, "lista_espera")
    promotion = decide(client, login(client, COORD), ready.id, "admitida")
    assert promotion.status_code == 202, "one fresh vote plus an old outvoted one must not admit"
    assert promotion.json()["state"] == "pending" and len(promotion.json()["votes"]) == 1


def test_votes_for_different_cohorts_do_not_add_up(client, db, ready):
    make_cohort(db, "COH-T-IA2")
    decide(client, login(client, SEL_IA), ready.id, cohort_id=IA_COHORT)
    r = decide(client, login(client, COORD), ready.id, cohort_id="COH-T-IA2")
    assert r.status_code == 202 and r.json()["state"] == "disagreement"


def test_history_shows_quorum_and_pending_votes(client, ready):
    decide(client, login(client, SEL_IA), ready.id)
    body = history(client, login(client, COORD), ready.id).json()
    assert body["quorum"] == 2 and len(body["pending_votes"]) == 1 and body["items"] == []


def test_quorum_one_keeps_the_single_signature_behaviour(client, db, ready):
    db.get(Call, IA_CALL).selection_quorum = 1
    db.commit()
    assert decide(client, login(client, SEL_IA), ready.id).status_code == 201


def test_full_call_is_rejected_on_the_first_vote(client, db, ready):
    admitted = db.scalar(select(func.count()).select_from(Application).where(Application.call_id == IA_CALL, Application.stage == "admitida"))
    db.get(Call, IA_CALL).plazas = admitted
    db.commit()
    r = decide(client, login(client, SEL_IA), ready.id)
    assert r.status_code == 409 and r.json()["code"] == "no_places_left"


# ---------- PR 98 review follow-ups: quorum configuration and concurrency ----------


def test_selection_and_coordination_read_the_policy(client):
    for account in (SEL_IA, COORD):
        r = client.get(f"/api/v1/calls/{IA_CALL}/selection-policy", headers=login(client, account))
        assert r.status_code == 200 and r.json() == {"selection_quorum": 2}


def test_only_administration_changes_the_quorum_and_it_is_audited(client, db):
    for account in (SEL_IA, COORD, CAPT_IA, DOCENTE):
        r = client.put(f"/api/v1/calls/{IA_CALL}/selection-policy", json={"selection_quorum": 1}, headers=login(client, account))
        assert r.status_code == 403, account
    r = client.put(f"/api/v1/calls/{IA_CALL}/selection-policy", json={"selection_quorum": 3}, headers=login(client, ADMIN))
    assert r.status_code == 200 and r.json() == {"selection_quorum": 3}
    db.expire_all()
    assert db.get(Call, IA_CALL).selection_quorum == 3
    event = db.scalar(select(AuditEvent).where(AuditEvent.action == "call.selection_policy_updated"))
    assert event.meta == {"selection_quorum_before": 2, "selection_quorum": 3}


@pytest.mark.parametrize("value", [0, 6, "dos"])
def test_quorum_outside_one_to_five_is_rejected(client, value):
    r = client.put(f"/api/v1/calls/{IA_CALL}/selection-policy", json={"selection_quorum": value}, headers=login(client, ADMIN))
    assert r.status_code == 422


def test_two_simultaneous_agreeing_votes_create_exactly_one_decision_and_enrollment(db, ready):
    """The application and the call are locked per vote, so the second vote sees the first: one decision, one enrollment."""
    from concurrent.futures import ThreadPoolExecutor

    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as one, TestClient(app) as two:
        who = [login(one, SEL_IA), login(two, COORD)]
        with ThreadPoolExecutor(2) as pool:
            codes = sorted(pool.map(lambda c, h: decide(c, h, ready.id).status_code, [one, two], who))
    assert codes == [201, 202]
    assert count(db, SelectionDecision, ready) == 1
    assert db.scalar(select(func.count()).select_from(Enrollment).where(Enrollment.application_id == ready.id)) == 1


def test_three_simultaneous_votes_with_quorum_two_still_decide_once(db, ready):
    from concurrent.futures import ThreadPoolExecutor

    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as one, TestClient(app) as two, TestClient(app) as three:
        clients = [one, two, three]
        who = [login(one, SEL_IA), login(two, COORD), login(three, ADMIN)]
        with ThreadPoolExecutor(3) as pool:
            codes = sorted(pool.map(lambda c, h: decide(c, h, ready.id).status_code, clients, who))
    assert codes[:2] == [201, 202] and codes[2] == 409  # the third arrives after the decision: selection already ended
    assert count(db, SelectionDecision, ready) == 1
    assert db.scalar(select(func.count()).select_from(Enrollment).where(Enrollment.application_id == ready.id)) == 1
