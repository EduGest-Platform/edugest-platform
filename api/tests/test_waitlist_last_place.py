from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.main import app
from app.modules.audit.models import AuditEvent
from app.modules.learning.models import Enrollment
from app.modules.selection.models import SelectionApproval, SelectionDecision
from tests.conftest import COORD, SEL_IA, login
from tests.test_own_selection_outcome import create_applicant_account, own_outcome_path
from tests.test_selection_decisions import decide, leave_one_place, make_application, make_cohort


def test_two_waitlisted_applications_contend_for_the_last_seat_at_final_signature(client, db):
    make_cohort(db)
    leave_one_place(db)
    applicants = [make_application(db), make_application(db)]
    applicant_ids = [application.id for application in applicants]
    owners = [login(client, create_applicant_account(db, application)) for application in applicants]
    selector = login(client, SEL_IA)
    coordinator = login(client, COORD)

    for application_id in applicant_ids:
        assert decide(client, selector, application_id, "lista_espera").status_code == 202
        assert decide(client, coordinator, application_id, "lista_espera").status_code == 201
        assert decide(client, selector, application_id).status_code == 202

    gate = Barrier(2)

    def sign_final_vote(http, application_id):
        gate.wait(timeout=8)
        return decide(http, coordinator, application_id)

    with TestClient(app) as first, TestClient(app) as second, ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(sign_final_vote, (first, second), applicant_ids))
    assert sorted(response.status_code for response in responses) == [201, 409]
    winner_index = next(index for index, response in enumerate(responses) if response.status_code == 201)
    loser_index = 1 - winner_index
    winner_id, loser_id = applicant_ids[winner_index], applicant_ids[loser_index]
    assert responses[loser_index].json()["code"] == "no_places_left"

    winner = client.get(own_outcome_path(winner_id), headers=owners[winner_index]).json()
    loser = client.get(own_outcome_path(loser_id), headers=owners[loser_index]).json()
    assert winner["outcome"] == "admitida"
    assert winner["enrollment"]["enrollment_id"] == responses[winner_index].json()["enrollment_id"]
    assert loser["outcome"] == "lista_espera" and loser["enrollment"] is None

    retry = decide(client, coordinator, winner_id)
    assert retry.status_code == 409 and retry.json()["code"] == "selection_ended"
    assert client.get(own_outcome_path(winner_id), headers=owners[winner_index]).json() == winner
    db.expire_all()
    enrollments = db.scalars(select(Enrollment).where(Enrollment.application_id.in_(applicant_ids))).all()
    assert [(row.application_id, str(row.id)) for row in enrollments] == [(winner_id, winner["enrollment"]["enrollment_id"])]
    decisions = db.scalars(select(SelectionDecision).where(
        SelectionDecision.application_id.in_(applicant_ids), SelectionDecision.decision == "admitida",
    )).all()
    decision, = decisions
    assert decision.application_id == winner_id
    votes = db.scalars(select(SelectionApproval).where(
        SelectionApproval.application_id.in_(applicant_ids), SelectionApproval.decision == "admitida",
    )).all()
    winning_votes = {vote.actor_user_id for vote in votes if vote.application_id == winner_id and vote.decision_id == decision.id}
    assert len(winning_votes) == 2
    loser_vote, = [vote for vote in votes if vote.application_id == loser_id]
    assert loser_vote.decision_id is None

    audit_rows = db.scalars(select(AuditEvent).where(
        AuditEvent.target_id.in_([str(value) for value in applicant_ids]), AuditEvent.action == "selection.decided",
    )).all()
    admitted_audit, = [row for row in audit_rows if row.meta["decision"] == "admitida"]
    assert admitted_audit.target_id == str(winner_id) and admitted_audit.meta["quorum"] == 2
