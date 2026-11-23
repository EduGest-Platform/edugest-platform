"""Melissa round 3 Q11: a selection decision needs two different people by default (configurable per call)."""

import pytest
from sqlalchemy import func, select

from app.modules.admissions.models import Application
from app.modules.audit.models import AuditEvent
from app.modules.catalog.models import Call
from app.modules.learning.models import Enrollment
from app.modules.selection.models import SelectionApproval, SelectionDecision
from tests.conftest import ADMIN, COORD, SEL_IA, login
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
    pending = db.scalars(select(SelectionApproval).where(SelectionApproval.application_id == ready.id, SelectionApproval.decision_id.is_(None))).all()
    assert [v.decision for v in pending] == ["admitida"]  # the outvoted vote stays visible, never applied


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
