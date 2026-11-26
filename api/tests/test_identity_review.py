"""KAN-274: an email already on file creates a separate record and a review that only a person in scope resolves."""

import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event, func, select
from sqlalchemy.exc import IntegrityError

from app.core.db import SessionLocal, utcnow
from app.main import app
from app.modules.admissions.models import Application, ApplicationEvent, IdentityReview
from app.modules.audit.models import AuditEvent
from app.modules.catalog.models import Call, Cohort
from app.modules.identity.models import Person, RoleAssignment, User
from app.modules.learning.models import Enrollment
from tests.conftest import ADMIN, ASPIRANTE, CAPT_DATA, CAPT_IA, COORD, DOCENTE, SEL_IA, login, new_application

IA_CALL, DATA_CALL, THIRD_CALL = "CONV-IA-2027A", "CONV-DATA-2027A", "CONV-IA-2026B"
EMAIL = "nueva.persona@example.test"
REASON = "Synthetic identity check by phone"


def apply(client, call_id=IA_CALL, headers=None, **over):
    response = client.post("/api/v1/applications", json=new_application(call_id=call_id, **over), headers=headers or {})
    assert response.status_code == 201, response.text
    return response.json()


def url(application) -> str:
    return f"/api/v1/applications/{application['id']}/identity-review"


def person_of(db, application):
    db.expire_all()
    return db.scalar(select(Application.person_id).where(Application.id == application["id"]))


def people_with(db, email=EMAIL) -> int:
    return db.scalar(select(func.count()).select_from(Person).where(Person.email == email))


def review_row(db, application):
    db.expire_all()
    return db.scalar(select(IdentityReview).where(IdentityReview.application_id == application["id"]))


def same_person(person_id) -> dict:
    return {"decision": "misma_persona", "linked_person_id": str(person_id), "reason": REASON}


DIFFERENT_PERSON = {"decision": "persona_distinta", "reason": REASON}


@pytest.fixture
def pair(client):
    """The same email applies to the IA call first and to the data call afterwards."""
    first = apply(client, IA_CALL, nombre="Primera Sintética")
    second = apply(client, DATA_CALL, nombre="Segunda Sintética", email=f"  {EMAIL.upper()} ")
    return first, second


@pytest.fixture
def third_call_open(db):
    db.get(Call, THIRD_CALL).estado = "abierta"
    db.commit()


def test_another_call_gets_a_separate_record_and_a_pending_review(client, db, pair):
    first, second = pair
    assert people_with(db) == 2
    assert person_of(db, first) != person_of(db, second)
    assert review_row(db, first) is None
    review = review_row(db, second)
    assert review.decision is None and review.original_person_id == person_of(db, second)


def test_the_public_receipt_reveals_nothing_about_other_records(client, pair):
    first, second = pair
    assert set(first) == set(second) == {"id", "codigo", "call_id", "stage", "created_at"}


def test_same_call_is_still_rejected_even_when_the_record_is_separate(client, db, pair):
    response = client.post("/api/v1/applications", json=new_application(call_id=DATA_CALL, email=EMAIL.title()))
    assert response.status_code == 409
    assert people_with(db) == 2


def test_a_first_time_email_raises_no_review(client):
    receipt = apply(client)
    body = client.get(url(receipt), headers=login(client, CAPT_IA)).json()
    assert body["status"] == "sin_coincidencias" and body["matches"] == []


def test_staff_in_scope_for_every_call_see_the_match(client, pair):
    first, second = pair
    body = client.get(url(second), headers=login(client, ADMIN)).json()
    assert body["status"] == "pendiente" and body["blocker"] is None and not body["has_hidden_matches"]
    assert body["submitted_name"] == "Segunda Sintética"
    [match] = body["matches"]
    assert match["display_name"] == "Primera Sintética"
    assert [a["codigo"] for a in match["applications"]] == [first["codigo"]]


def test_a_match_outside_scope_is_announced_without_details_and_cannot_be_resolved(client, db, pair):
    first, second = pair
    headers = login(client, CAPT_DATA)
    shown = client.get(url(second), headers=headers)
    assert shown.json()["blocker"] == "fuera_de_ambito" and shown.json()["has_hidden_matches"]
    assert shown.json()["matches"] == []
    for secret in (first["codigo"], first["id"], IA_CALL, "Primera", str(person_of(db, first))):
        assert secret not in shown.text

    before = person_of(db, second)
    for body in (DIFFERENT_PERSON, same_person(person_of(db, first))):
        assert client.post(url(second), headers=headers, json=body).status_code == 403
    assert person_of(db, second) == before and review_row(db, second).decision is None
    assert db.scalar(select(func.count()).select_from(AuditEvent).where(AuditEvent.action == "application.identity_review_denied")) == 2


def test_scope_over_both_calls_is_enough_to_resolve(client, db, pair):
    first, second = pair
    staff = db.scalar(select(User.id).where(User.email == CAPT_DATA))
    db.add(RoleAssignment(user_id=staff, role="captacion", scope_type="call", scope_id=IA_CALL))
    db.commit()
    response = client.post(url(second), headers=login(client, CAPT_DATA), json=same_person(person_of(db, first)))
    assert response.status_code == 201, response.text


@pytest.mark.parametrize("account", [COORD, DOCENTE, ASPIRANTE, CAPT_IA, SEL_IA])
def test_profiles_without_crm_access_to_the_application_get_403(client, db, pair, account):
    """Includes IA staff: they have CRM access to the match but not to the data application under review."""
    _, second = pair
    headers = login(client, account)
    assert client.get(url(second), headers=headers).status_code == 403
    assert client.post(url(second), headers=headers, json=DIFFERENT_PERSON).status_code == 403
    assert review_row(db, second).decision is None


def test_the_review_needs_a_session(client, pair):
    _, second = pair
    assert client.get(url(second)).status_code == 401
    assert client.post(url(second), json=DIFFERENT_PERSON).status_code == 401


def test_confirming_the_same_person_links_and_records_who_when_and_why(client, db, pair):
    first, second = pair
    original = person_of(db, second)
    updated_before = db.get(Application, second["id"]).updated_at
    response = client.post(url(second), headers=login(client, ADMIN), json=same_person(person_of(db, first)))
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["status"] == "misma_persona" and body["reason"] == REASON and body["decided_by"] and body["decided_at"]
    assert body["submitted_name"] == "Segunda Sintética"

    assert person_of(db, second) == person_of(db, first)
    assert db.get(Application, second["id"]).updated_at == updated_before
    review = review_row(db, second)
    assert review.original_person_id == original and review.linked_person_id == person_of(db, first)
    assert review.decided_by == db.scalar(select(User.id).where(User.email == ADMIN))


def test_deciding_they_are_different_people_keeps_both_records(client, db, pair):
    first, second = pair
    response = client.post(url(second), headers=login(client, ADMIN), json=DIFFERENT_PERSON)
    assert response.status_code == 201, response.text
    assert response.json()["status"] == "persona_distinta"
    assert person_of(db, first) != person_of(db, second)
    assert review_row(db, second).linked_person_id is None


def test_history_and_audit_keep_the_reason_and_personal_data_out(client, db, pair):
    first, second = pair
    client.post(url(second), headers=login(client, ADMIN), json=same_person(person_of(db, first)))
    summaries = db.scalars(select(ApplicationEvent.resumen).where(ApplicationEvent.application_id == second["id"])).all()
    assert any("misma persona" in text for text in summaries)
    assert not any(REASON in text or "Sintética" in text for text in summaries)
    rows = db.scalars(select(AuditEvent).where(AuditEvent.action.in_(["application.created", "application.identity_reviewed"]))).all()
    meta = str([row.meta for row in rows])
    for secret in (EMAIL, "Sintética", REASON):
        assert secret not in meta


def test_a_review_is_decided_only_once(client, db, pair):
    first, second = pair
    headers = login(client, ADMIN)
    assert client.post(url(second), headers=headers, json=DIFFERENT_PERSON).status_code == 201
    assert client.post(url(second), headers=headers, json=same_person(person_of(db, first))).status_code == 409
    assert review_row(db, second).decision == "persona_distinta"


def test_there_is_nothing_to_decide_without_a_review(client, pair):
    first, _ = pair
    assert client.post(url(first), headers=login(client, ADMIN), json=DIFFERENT_PERSON).status_code == 409


@pytest.mark.parametrize(
    "body",
    [
        {"decision": "persona_distinta", "reason": "   "},
        {"decision": "persona_distinta"},
        {"decision": "misma_persona", "reason": REASON},
        {"decision": "persona_distinta", "reason": REASON, "linked_person_id": "00000000-0000-0000-0000-000000000001"},
        {"decision": "misma_persona", "reason": REASON, "linked_person_id": "00000000-0000-0000-0000-000000000001"},
        {"decision": "otra", "reason": REASON},
    ],
)
def test_incomplete_or_foreign_decisions_are_rejected(client, db, pair, body):
    _, second = pair
    assert client.post(url(second), headers=login(client, ADMIN), json=body).status_code == 422
    assert review_row(db, second).decision is None


def test_an_existing_record_that_is_not_a_match_cannot_be_linked(client, db, pair):
    _, second = pair
    unrelated = apply(client, IA_CALL, email="otra.sintetica@example.test")
    before = person_of(db, second)
    response = client.post(url(second), headers=login(client, ADMIN), json=same_person(person_of(db, unrelated)))
    assert response.status_code == 422
    assert person_of(db, second) == before and review_row(db, second).decision is None


def test_a_match_with_applications_in_two_calls_needs_scope_over_both(client, db, pair, third_call_open):
    first, second = pair
    assert client.post(url(second), headers=login(client, ADMIN), json=same_person(person_of(db, first))).status_code == 201
    third = apply(client, THIRD_CALL)
    # IA recruitment covers one of the two calls of the match, not the data one.
    headers = login(client, CAPT_IA)
    body = client.get(url(third), headers=headers).json()
    assert body["blocker"] == "fuera_de_ambito" and body["matches"] == []
    assert client.post(url(third), headers=headers, json=DIFFERENT_PERSON).status_code == 403


def test_one_hidden_match_blocks_the_decision_even_with_another_in_view(client, db, pair, third_call_open):
    first, second = pair
    client.post(url(second), headers=login(client, ADMIN), json=DIFFERENT_PERSON)
    third = apply(client, THIRD_CALL)
    headers = login(client, CAPT_IA)
    body = client.get(url(third), headers=headers).json()
    assert [m["person_id"] for m in body["matches"]] == [str(person_of(db, first))]
    assert body["has_hidden_matches"] and body["blocker"] == "fuera_de_ambito"
    for decision in (DIFFERENT_PERSON, same_person(person_of(db, first))):
        assert client.post(url(third), headers=headers, json=decision).status_code == 403
    assert review_row(db, third).decision is None


def test_after_the_decision_the_reason_keeps_the_scope_rule(client, db, pair):
    first, second = pair
    decision = {**same_person(person_of(db, first)), "reason": f"Same as {first['codigo']}"}
    assert client.post(url(second), headers=login(client, ADMIN), json=decision).status_code == 201
    narrow = client.get(url(second), headers=login(client, CAPT_DATA))
    assert narrow.json()["status"] == "misma_persona" and narrow.json()["reason"] is None
    assert first["codigo"] not in narrow.text
    assert client.get(url(second), headers=login(client, ADMIN)).json()["reason"] == decision["reason"]


def test_each_look_and_decision_is_audited_with_codes_only(client, db, pair):
    _, second = pair
    outsider, admin = login(client, CAPT_DATA), login(client, ADMIN)
    client.get(url(second), headers=outsider)
    client.post(url(second), headers=outsider, json=DIFFERENT_PERSON)
    client.post(url(second), headers=admin, json=DIFFERENT_PERSON)

    def only(action):
        row, = db.scalars(select(AuditEvent).where(AuditEvent.action == f"application.{action}")).all()
        return row

    def account(email):
        return db.scalar(select(User.id).where(User.email == email))

    viewed, denied, reviewed = only("identity_review_viewed"), only("identity_review_denied"), only("identity_reviewed")
    assert viewed.meta == {"codigo": second["codigo"], "matches_shown": 0} and viewed.actor_user_id == account(CAPT_DATA)
    assert denied.meta == {"codigo": second["codigo"]} and denied.actor_user_id == account(CAPT_DATA)
    assert reviewed.meta == {"codigo": second["codigo"], "decision": "persona_distinta"} and reviewed.actor_user_id == account(ADMIN)


def test_two_simultaneous_decisions_record_only_one(client, db, pair):
    first, second = pair
    headers = login(client, ADMIN)
    bodies = [DIFFERENT_PERSON, same_person(person_of(db, first))]
    gate = threading.Barrier(len(bodies))

    def submit(body):
        with TestClient(app) as other:
            gate.wait(timeout=8)
            return other.post(url(second), headers=headers, json=body).status_code

    with ThreadPoolExecutor(max_workers=len(bodies)) as pool:
        codes = sorted(pool.map(submit, bodies))
    assert codes == [201, 409]
    db.expire_all()
    notes = select(func.count()).select_from(ApplicationEvent).where(ApplicationEvent.application_id == second["id"], ApplicationEvent.tipo == "nota")
    assert db.scalar(notes) == 1


def test_earlier_reviews_are_resolved_first_and_merged_records_stop_matching(client, db, pair, third_call_open):
    first, second = pair
    third = apply(client, THIRD_CALL)
    headers = login(client, ADMIN)
    shown = client.get(url(third), headers=headers).json()
    assert shown["blocker"] == "revision_anterior_pendiente" and len(shown["matches"]) == 2
    assert client.post(url(third), headers=headers, json=DIFFERENT_PERSON).status_code == 409

    assert client.post(url(second), headers=headers, json=same_person(person_of(db, first))).status_code == 201
    shown = client.get(url(third), headers=headers).json()
    assert shown["blocker"] is None
    assert [m["person_id"] for m in shown["matches"]] == [str(person_of(db, first))]
    assert len(shown["matches"][0]["applications"]) == 2


def test_records_kept_apart_are_both_offered_to_the_next_review(client, db, pair, third_call_open):
    _, second = pair
    third = apply(client, THIRD_CALL)
    headers = login(client, ADMIN)
    client.post(url(second), headers=headers, json=DIFFERENT_PERSON)
    shown = client.get(url(third), headers=headers).json()
    assert shown["blocker"] is None and len(shown["matches"]) == 2


def test_nobody_is_admitted_while_the_review_is_pending(client, db, pair):
    first, second = pair
    db.get(Call, DATA_CALL).selection_quorum = 1
    db.get(Application, second["id"]).stage = "pendiente_decision_humana"
    db.commit()
    headers = login(client, ADMIN)
    decisions = f"/api/v1/applications/{second['id']}/selection-decisions"
    admit = {"decision": "admitida", "reason": "Synthetic selection decision", "cohort_id": "COH-DATA-2027A"}
    enrollments = db.scalar(select(func.count()).select_from(Enrollment))

    blocked = client.post(decisions, headers=headers, json=admit)
    assert blocked.status_code == 409 and blocked.json()["code"] == "dossier_check_pending"
    db.expire_all()
    assert db.scalar(select(func.count()).select_from(Enrollment)) == enrollments

    assert client.post(url(second), headers=headers, json=same_person(person_of(db, first))).status_code == 201
    assert client.post(decisions, headers=headers, json=admit).status_code == 201
    db.expire_all()
    assert db.scalar(select(Enrollment.person_id).where(Enrollment.application_id == second["id"])) == person_of(db, first)


def test_a_signed_in_person_applying_with_their_own_email_keeps_their_record(client, db):
    headers = login(client, ASPIRANTE)
    receipt = apply(client, headers=headers, email=ASPIRANTE)
    assert people_with(db, ASPIRANTE) == 1 and review_row(db, receipt) is None
    assert [a["id"] for a in client.get("/api/v1/me/applications", headers=headers).json()] == [receipt["id"]]


def test_an_anonymous_application_reaches_an_account_only_after_a_human_decision(client, db):
    receipt = apply(client, email=ASPIRANTE)
    mine = login(client, ASPIRANTE)
    assert client.get("/api/v1/me/applications", headers=mine).json() == []

    admin = login(client, ADMIN)
    [match] = client.get(url(receipt), headers=admin).json()["matches"]
    assert client.post(url(receipt), headers=admin, json=same_person(match["person_id"])).status_code == 201
    assert [a["id"] for a in client.get("/api/v1/me/applications", headers=mine).json()] == [receipt["id"]]


def test_a_signed_in_account_cannot_attach_someone_elses_email(client, db, pair):
    headers = login(client, ASPIRANTE)
    third = apply(client, DATA_CALL, headers=headers, email="otra.sintetica@example.test")
    assert client.get("/api/v1/me/applications", headers=headers).json() == []
    assert people_with(db, "otra.sintetica@example.test") == 1 and review_row(db, third) is None


def test_two_simultaneous_intakes_with_one_new_email_cannot_miss_each_other(db):
    """While the first intake is still open, the second one has to wait for the email lock."""
    state = {"thread": None, "waited": None, "status": None}

    def submit_second():
        with TestClient(app) as other:
            state["status"] = other.post("/api/v1/applications", json=new_application(call_id=DATA_CALL)).status_code

    def start_competitor(mapper, connection, target):
        if state["thread"] is None and target.email == EMAIL:
            state["thread"] = threading.Thread(target=submit_second)
            state["thread"].start()
            state["thread"].join(timeout=2)
            state["waited"] = state["thread"].is_alive()

    event.listen(Person, "before_insert", start_competitor)
    try:
        with TestClient(app) as client:
            assert client.post("/api/v1/applications", json=new_application()).status_code == 201
    finally:
        event.remove(Person, "before_insert", start_competitor)
        if state["thread"] is not None:
            state["thread"].join(timeout=30)

    assert state["waited"] is True and state["status"] == 201
    assert people_with(db) == 2
    assert db.scalar(select(func.count()).select_from(IdentityReview)) == 1


@pytest.mark.parametrize(
    "values",
    [
        {"decision": "persona_distinta"},
        {"reason": REASON},
        {"decision": "misma_persona", "reason": REASON, "decided": True},
        {"decision": "persona_distinta", "reason": "  ", "decided": True},
        {"decision": "otra", "reason": REASON, "decided": True},
    ],
)
def test_the_database_rejects_half_recorded_decisions(client, db, pair, values):
    _, second = pair
    review = review_row(db, second)
    if values.pop("decided", False):
        values.update(decided_by=db.scalar(select(User.id).where(User.email == ADMIN)), decided_at=utcnow())
    for name, value in values.items():
        setattr(review, name, value)
    with pytest.raises(IntegrityError):
        db.commit()
    with SessionLocal() as check:
        assert check.get(IdentityReview, second["id"]).decision is None


def enrolled_only_record(db, email=EMAIL) -> Person:
    """A record that is only enrolled in a data cohort with no call behind it."""
    db.add(Cohort(id="COH-T-NOCALL", program_id="P-DATA", call_id=None, nombre="Synthetic cohort without call",
                  inicio=date(2027, 3, 1), fin=date(2027, 9, 30)))
    person = Person(display_name="Matriculada Sintética", email=email, is_synthetic=True)
    db.add(person)
    db.flush()
    db.add(Enrollment(person_id=person.id, cohort_id="COH-T-NOCALL", estado="activa"))
    db.commit()
    return person


def test_an_enrollment_without_a_call_still_needs_scope_over_its_programme(client, db):
    record = enrolled_only_record(db)
    receipt = apply(client, IA_CALL)
    outsider = login(client, CAPT_IA)
    shown = client.get(url(receipt), headers=outsider)
    assert shown.json()["blocker"] == "fuera_de_ambito" and "Matriculada" not in shown.text
    assert client.post(url(receipt), headers=outsider, json=same_person(record.id)).status_code == 403
    assert person_of(db, receipt) != record.id

    staff = db.scalar(select(User.id).where(User.email == CAPT_IA))
    db.add(RoleAssignment(user_id=staff, role="captacion", scope_type="program", scope_id="P-DATA"))
    db.commit()
    assert [m["person_id"] for m in client.get(url(receipt), headers=login(client, CAPT_IA)).json()["matches"]] == [str(record.id)]


def test_a_record_that_is_only_an_account_needs_global_access(client, db):
    record = Person(display_name="Cuenta Sintética", email=EMAIL, is_synthetic=True)
    db.add(record)
    db.flush()
    db.add(User(email=EMAIL, display_name="Cuenta Sintética", password_hash="not-a-password", person_id=record.id))
    db.commit()
    receipt = apply(client, IA_CALL)

    outsider = login(client, CAPT_IA)
    assert client.get(url(receipt), headers=outsider).json()["blocker"] == "fuera_de_ambito"
    assert client.post(url(receipt), headers=outsider, json=same_person(record.id)).status_code == 403
    assert [m["person_id"] for m in client.get(url(receipt), headers=login(client, ADMIN)).json()["matches"]] == [str(record.id)]


def test_a_skewed_clock_cannot_hide_a_duplicate(client, db):
    first = apply(client, IA_CALL)
    db.get(Person, person_of(db, first)).created_at = utcnow() + timedelta(hours=1)
    db.commit()
    second = apply(client, DATA_CALL)
    shown = client.get(url(second), headers=login(client, ADMIN)).json()
    assert shown["status"] == "pendiente" and len(shown["matches"]) == 1
