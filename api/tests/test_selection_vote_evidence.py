"""KAN-200: closed decisions retain their linked human votes without widening scope."""

from sqlalchemy import select

from app.modules.identity.models import User
from app.modules.selection.models import SelectionDecision
from tests.conftest import ADMIN, COORD, SEL_IA, login
from tests.test_selection_decisions import DATA_CALL, IA_CALL, decide, history, make_application, make_cohort


def apply_pair(client, target, first="lista_espera", second=None):
    second = second or first
    pending = decide(client, login(client, SEL_IA), target.id, first, reason="Synthetic first review")
    assert pending.status_code == 202
    applied = decide(client, login(client, COORD), target.id, second, reason="Synthetic second review")
    return pending, applied


def test_applied_response_and_history_keep_the_two_human_votes(client, db):
    make_cohort(db)
    target = make_application(db)
    pending, applied = apply_pair(client, target, "admitida")
    assert applied.status_code == 201
    votes = applied.json()["votes"]
    assert len(votes) == 2
    assert votes[0] == pending.json()["votes"][0]
    assert [row["reason"] for row in votes] == ["Synthetic first review", "Synthetic second review"]
    expected_names = set(db.scalars(select(User.display_name).where(User.email.in_([SEL_IA, COORD]))))
    assert {row["actor"] for row in votes} == expected_names
    assert all(set(row) == {"decision", "cohort_id", "reason", "actor", "occurred_at"} for row in votes)
    response = history(client, login(client, SEL_IA), target.id)
    assert response.status_code == 200
    assert response.json()["pending_votes"] == []
    assert response.json()["items"][0]["votes"] == votes


def test_disagreeing_votes_remain_visible_instead_of_appearing_unanimous(client, db):
    make_cohort(db)
    target = make_application(db)
    _, split = apply_pair(client, target, "admitida", "lista_espera")
    assert split.status_code == 202 and split.json()["state"] == "disagreement"
    applied = decide(client, login(client, ADMIN), target.id, "lista_espera", reason="Synthetic tie resolution")
    assert applied.status_code == 201
    votes = applied.json()["votes"]
    assert [row["decision"] for row in votes] == ["admitida", "lista_espera", "lista_espera"]
    assert history(client, login(client, SEL_IA), target.id).json()["items"][0]["votes"] == votes


def test_policy_change_does_not_rewrite_closed_vote_evidence(client, db):
    target = make_application(db)
    _, applied = apply_pair(client, target)
    assert applied.status_code == 201
    votes = applied.json()["votes"]
    changed = client.put(f"/api/v1/calls/{IA_CALL}/selection-policy", headers=login(client, ADMIN), json={"selection_quorum": 3})
    assert changed.status_code == 200
    result = history(client, login(client, SEL_IA), target.id).json()
    assert result["quorum"] == 3  # Current policy, not a reconstruction of the old decision's policy.
    assert result["items"][0]["votes"] == votes and len(votes) == 2


def test_waiting_and_later_admission_keep_separate_vote_groups(client, db):
    make_cohort(db)
    target = make_application(db)
    _, waiting = apply_pair(client, target, "lista_espera")
    assert waiting.status_code == 201
    _, admitted = apply_pair(client, target, "admitida")
    assert admitted.status_code == 201
    items = history(client, login(client, SEL_IA), target.id).json()["items"]
    assert len(items) == 2
    assert items[0]["votes"] == waiting.json()["votes"]
    assert items[1]["votes"] == admitted.json()["votes"]
    assert all(vote["decision"] == "lista_espera" for vote in items[0]["votes"])
    assert all(vote["decision"] == "admitida" for vote in items[1]["votes"])


def test_legacy_decision_without_linked_votes_returns_no_fabricated_approvals(client, db):
    target = make_application(db, stage="lista_espera")
    actor_id = db.scalars(select(User.id).where(User.email == ADMIN)).one()
    db.add(SelectionDecision(application_id=target.id, decision="lista_espera", from_stage="pendiente_decision_humana",
                             to_stage="lista_espera", reason="Synthetic legacy decision", actor_user_id=actor_id))
    db.commit()
    response = history(client, login(client, SEL_IA), target.id)
    assert response.status_code == 200
    assert response.json()["items"][0]["votes"] == []


def test_foreign_call_vote_evidence_is_still_forbidden(client, db):
    target = make_application(db, call_id=DATA_CALL)
    assert decide(client, login(client, ADMIN), target.id, "lista_espera", reason="Synthetic foreign review").status_code == 202
    assert decide(client, login(client, COORD), target.id, "lista_espera", reason="Synthetic foreign confirmation").status_code == 201
    denied = history(client, login(client, SEL_IA), target.id)
    assert denied.status_code == 403
    assert "Synthetic foreign" not in denied.text
    assert "votes" not in denied.json()
