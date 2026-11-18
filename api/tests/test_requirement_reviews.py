"""KAN-128 · requirement reviews: persistence, human exceptions, scope isolation, history and concurrency."""

import json
import os

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import func, inspect, select
from sqlalchemy.exc import IntegrityError

from app.core import audit
from app.core.authz import ROLE_PERMISSIONS
from app.core.db import engine, utcnow
from app.main import app
from app.modules.admissions.models import Application, ApplicationEvent
from app.modules.audit.models import AuditEvent
from app.modules.identity.models import Person, User
from app.modules.learning.models import Enrollment
from app.modules.requirements.models import RequirementReview, RequirementReviewRevision
from tests.conftest import ADMIN, API_DIR, ASPIRANTE, CAPT_DATA, CAPT_IA, CODER, COORD, DOCENTE, SEL_IA, login

IA_CALL, DATA_CALL, IA_CLOSED_CALL = "CONV-IA-2027A", "CONV-DATA-2027A", "CONV-IA-2026B"
REF = "identity-document"
REASON = "Documento comprobado en la revisión"


def application_in(db, call_id) -> Application:
    found = db.scalar(select(Application).where(Application.call_id == call_id).order_by(Application.codigo))
    assert found is not None, call_id
    return found


def closed_call_application(db) -> Application:
    """The closed IA call feeds COH-IA, so a teacher of that cohort has scope over its applications."""
    person = db.scalar(select(Person).order_by(Person.email))
    created = Application(
        codigo="IA26B-0001", person_id=person.id, call_id=IA_CLOSED_CALL, stage="convocada",
        motivacion="Motivación sintética de prueba", disponibilidad="Flexible", acepta_datos_sinteticos=True,
    )
    db.add(created)
    db.commit()
    db.refresh(created)
    return created


def reviews_url(application) -> str:
    return f"/api/v1/applications/{application.id}/requirement-reviews"


def put_review(client, who, application, result, reason=REASON, ref=REF, **extra):
    return client.put(f"{reviews_url(application)}/{ref}", json={"result": result, "reason": reason, **extra}, headers=who)


def counts(db) -> tuple[int, int, int]:
    """(reviews, revisions, requirement audit events): what a rejected request must leave untouched."""
    db.expire_all()
    audit_rows = select(func.count()).select_from(AuditEvent).where(AuditEvent.action.like("requirement_review.%"))
    return (
        db.scalar(select(func.count()).select_from(RequirementReview)),
        db.scalar(select(func.count()).select_from(RequirementReviewRevision)),
        db.scalar(audit_rows),
    )


def display_name(db, email) -> str:
    return db.scalar(select(User.display_name).where(User.email == email))


def test_review_is_saved_with_server_author_and_date_and_survives_a_new_session(client, db):
    target = application_in(db, IA_CALL)
    created = put_review(client, login(client, CAPT_IA), target, "met")
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["reviewer"] == display_name(db, CAPT_IA) and body["reviewed_at"] and body["version"] == 1

    with TestClient(app) as other_session:
        listed = other_session.get(reviews_url(target), headers=login(other_session, SEL_IA))
    assert listed.status_code == 200
    assert listed.json()["items"] == [body]


@pytest.mark.parametrize("path", [["not_met"], ["met"], ["not_met", "exception_under_review", "exception_approved"]])
def test_review_results_never_change_the_stage_or_create_decisions(client, db, path):
    target = application_in(db, IA_CALL)
    target.stage = "evaluacion_en_curso"
    db.commit()
    events = db.scalar(select(func.count()).select_from(ApplicationEvent))
    enrollments = db.scalar(select(func.count()).select_from(Enrollment))
    admin, version = login(client, ADMIN), None
    for result in path:
        response = put_review(client, admin, target, result, expected_version=version)
        assert response.status_code in (200, 201), response.text
        version = response.json()["version"]
    db.expire_all()
    assert db.get(Application, target.id).stage == "evaluacion_en_curso"
    assert db.scalar(select(func.count()).select_from(ApplicationEvent)) == events
    assert db.scalar(select(func.count()).select_from(Enrollment)) == enrollments


# (who records the exception, call of the application): each one within its own scope.
EXCEPTION_WRITERS = [
    (ADMIN, IA_CALL), (CAPT_IA, IA_CALL), (SEL_IA, IA_CALL), (COORD, IA_CALL), (DOCENTE, IA_CLOSED_CALL),
]
READERS = {
    IA_CALL: [ADMIN, CAPT_IA, SEL_IA, COORD],
    IA_CLOSED_CALL: [ADMIN, CAPT_IA, COORD, DOCENTE],
}


@pytest.mark.parametrize(("writer", "call_id"), EXCEPTION_WRITERS)
def test_exception_recorded_by_any_allowed_role_is_visible_to_the_others_in_scope(client, db, writer, call_id):
    target = closed_call_application(db) if call_id == IA_CLOSED_CALL else application_in(db, call_id)
    assert put_review(client, login(client, ADMIN), target, "not_met").status_code == 201
    recorded = put_review(client, login(client, writer), target, "exception_under_review", reason="Excepción por causa justificada", expected_version=1)
    assert recorded.status_code == 200, recorded.text
    for reader in READERS[call_id]:
        seen = client.get(reviews_url(target), headers=login(client, reader)).json()["items"][0]
        assert seen["result"] == "exception_under_review"
        assert seen["reviewer"] == display_name(db, writer)
        assert seen["reason"] == "Excepción por causa justificada" and seen["reviewed_at"]


@pytest.mark.parametrize(("who", "call_id"), [(COORD, IA_CALL), (DOCENTE, IA_CLOSED_CALL)])
def test_coordination_and_teachers_cannot_record_met_or_not_met(client, db, who, call_id):
    target = closed_call_application(db) if call_id == IA_CLOSED_CALL else application_in(db, call_id)
    before = counts(db)
    for result in ("met", "not_met"):
        assert put_review(client, login(client, who), target, result).status_code == 403
    assert counts(db) == before


def test_anonymous_and_person_accounts_are_denied_without_writes(client, db):
    target = application_in(db, IA_CALL)
    before = counts(db)
    url = f"{reviews_url(target)}/{REF}"
    assert client.get(reviews_url(target)).status_code == 401
    assert client.put(url, json={"result": "met", "reason": REASON}).status_code == 401
    assert client.get(f"{url}/history").status_code == 401
    for person_account in (ASPIRANTE, CODER):
        who = login(client, person_account)
        assert client.get(reviews_url(target), headers=who).status_code == 403
        assert put_review(client, who, target, "met").status_code == 403
    assert counts(db) == before


def test_other_calls_cannot_be_read_or_written_by_an_otherwise_valid_role(client, db):
    ia_app, data_app = application_in(db, IA_CALL), application_in(db, DATA_CALL)
    assert put_review(client, login(client, ADMIN), ia_app, "met").status_code == 201
    before = counts(db)
    outsiders = [(CAPT_DATA, ia_app), (SEL_IA, data_app), (DOCENTE, ia_app)]
    for email, target in outsiders:
        who = login(client, email)
        assert client.get(reviews_url(target), headers=who).status_code == 403
        assert client.get(f"{reviews_url(target)}/{REF}/history", headers=who).status_code == 403
        assert put_review(client, who, target, "not_met").status_code == 403
    assert counts(db) == before


def test_unknown_application_and_malformed_requirement_ref(client, db):
    admin = login(client, ADMIN)
    missing = "/api/v1/applications/00000000-0000-0000-0000-000000000000/requirement-reviews"
    assert client.get(missing, headers=admin).status_code == 404
    target = application_in(db, IA_CALL)
    for bad_ref in ("UPPER", "-start", "with space", "x" * 61):
        assert put_review(client, admin, target, "met", ref=bad_ref).status_code == 422
    assert counts(db) == (0, 0, 0)


INVALID_BODIES = [
    {"result": "approved", "reason": REASON},
    {"result": "pending", "reason": REASON},
    {"result": "met", "reason": ""},
    {"result": "met", "reason": "   "},
    {"result": "met", "reason": "\t\n"},
    {"result": "met", "reason": "  "},
    {"result": "met", "reason": "x" * 501},
    {"result": "met", "reason": 12345},
    {"result": "met", "reason": None},
    {"result": "met"},
    {"result": "met", "reason": REASON, "expected_version": 0},
    {"result": "met", "reason": REASON, "reviewer": "Otra persona"},
    {"result": "met", "reason": REASON, "reviewer_user_id": "00000000-0000-0000-0000-000000000000"},
    {"result": "met", "reason": REASON, "reviewed_at": "2020-01-01T00:00:00Z"},
]


@pytest.mark.parametrize("body", INVALID_BODIES)
def test_invalid_input_and_spoofed_author_or_date_are_rejected_without_writes(client, db, body):
    target = application_in(db, IA_CALL)
    response = client.put(f"{reviews_url(target)}/{REF}", json=body, headers=login(client, ADMIN))
    assert response.status_code == 422, response.text
    assert counts(db) == (0, 0, 0)


def test_reason_is_trimmed_before_the_length_limit(client, db):
    target, admin = application_in(db, IA_CALL), login(client, ADMIN)
    padded = put_review(client, admin, target, "met", reason="  " + "x" * 500 + "  ")
    assert padded.status_code == 201 and len(padded.json()["reason"]) == 500
    too_long = put_review(client, admin, target, "not_met", reason="x" * 501, ref="second-requirement")
    assert too_long.status_code == 422


def test_revision_keeps_the_previous_reviewer_result_date_and_reason(client, db):
    target = application_in(db, IA_CALL)
    first = put_review(client, login(client, CAPT_IA), target, "met", reason="Primera revisión").json()
    second = put_review(client, login(client, SEL_IA), target, "not_met", reason="Corrección tras segunda lectura", expected_version=1)
    assert second.status_code == 200 and second.json()["version"] == 2

    history = client.get(f"{reviews_url(target)}/{REF}/history", headers=login(client, ADMIN)).json()["items"]
    assert [(h["revision"], h["result"], h["reviewer"], h["reason"]) for h in history] == [
        (1, "met", display_name(db, CAPT_IA), "Primera revisión"),
        (2, "not_met", display_name(db, SEL_IA), "Corrección tras segunda lectura"),
    ]
    assert history[0]["reviewed_at"] == first["reviewed_at"]
    current = client.get(reviews_url(target), headers=login(client, ADMIN)).json()["items"]
    assert [(c["result"], c["version"]) for c in current] == [("not_met", 2)]


def test_failed_save_leaves_review_history_and_audit_unchanged(db, monkeypatch):
    target = application_in(db, IA_CALL)
    with TestClient(app, raise_server_exceptions=False) as quiet_client:
        admin = login(quiet_client, ADMIN)
        assert put_review(quiet_client, admin, target, "met").status_code == 201
        before = counts(db)

        def fail(*_args, **_kwargs):
            raise RuntimeError("audit sink down")

        monkeypatch.setattr(audit, "record", fail)
        revised = put_review(quiet_client, admin, target, "not_met", reason="Cambio que no debe guardarse", expected_version=1)
        assert revised.status_code == 500
        monkeypatch.undo()
        assert counts(db) == before
        db.expire_all()
        saved = db.scalar(select(RequirementReview))
        assert (saved.result, saved.version, saved.reason) == ("met", 1, REASON)

        first_ever = put_review(quiet_client, admin, target, "met", ref="another-requirement")
        assert first_ever.status_code == 201


def test_stale_repeated_and_misplaced_versions_are_rejected(client, db):
    target, admin = application_in(db, IA_CALL), login(client, ADMIN)
    assert put_review(client, admin, target, "met", expected_version=1).status_code == 409  # nothing to revise yet
    assert counts(db) == (0, 0, 0)
    assert put_review(client, admin, target, "met").status_code == 201
    assert put_review(client, admin, target, "not_met").status_code == 409  # existing review needs its version
    assert put_review(client, admin, target, "not_met", expected_version=5).status_code == 409
    assert put_review(client, admin, target, "not_met", expected_version=1).status_code == 200
    assert put_review(client, admin, target, "not_met", expected_version=1).status_code == 409  # retry of the same write
    assert counts(db)[:2] == (1, 2)


@pytest.mark.parametrize(
    ("path", "forbidden"),
    [(["met"], "exception_approved"), (["not_met"], "exception_approved"), (["met"], "exception_under_review"), (["exception_under_review", "exception_approved"], "met")],
)
def test_result_changes_outside_the_allowed_transitions_are_rejected(client, db, path, forbidden):
    target, admin, version = application_in(db, IA_CALL), login(client, ADMIN), None
    for result in path:
        response = put_review(client, admin, target, result, expected_version=version)
        assert response.status_code in (200, 201), response.text
        version = response.json()["version"]
    assert put_review(client, admin, target, forbidden, expected_version=version).status_code == 409
    assert counts(db)[1] == len(path)


def test_first_review_cannot_start_as_an_approved_exception(client, db):
    target = application_in(db, IA_CALL)
    assert put_review(client, login(client, ADMIN), target, "exception_approved").status_code == 409
    assert counts(db) == (0, 0, 0)


def test_same_result_with_a_new_reason_is_an_amendment(client, db):
    target, admin = application_in(db, IA_CALL), login(client, ADMIN)
    put_review(client, admin, target, "met")
    amended = put_review(client, admin, target, "met", reason="Motivo ampliado", expected_version=1)
    assert amended.status_code == 200 and amended.json()["version"] == 2


def test_taking_or_undoing_an_exception_needs_the_exception_permission(client, db, monkeypatch):
    review_only = {"applications.read", "requirements.read", "requirements.review"}
    monkeypatch.setitem(ROLE_PERMISSIONS, "captacion", review_only)
    target, admin, recruiter = application_in(db, IA_CALL), login(client, ADMIN), login(client, CAPT_IA)
    assert put_review(client, admin, target, "not_met").status_code == 201
    assert put_review(client, recruiter, target, "exception_under_review", expected_version=1).status_code == 403
    assert put_review(client, admin, target, "exception_under_review", expected_version=1).status_code == 200
    assert put_review(client, admin, target, "exception_approved", expected_version=2).status_code == 200
    assert put_review(client, recruiter, target, "not_met", expected_version=3).status_code == 403
    assert put_review(client, admin, target, "not_met", expected_version=3).status_code == 200


def test_no_reviews_means_not_reviewed_and_missing_history_is_404(client, db):
    target, admin = application_in(db, IA_CALL), login(client, ADMIN)
    listed = client.get(reviews_url(target), headers=admin)
    assert listed.status_code == 200 and listed.json()["items"] == []
    assert client.get(f"{reviews_url(target)}/{REF}/history", headers=admin).status_code == 404


def test_audit_events_carry_no_free_text_or_personal_data(client, db):
    target, secret_reason = application_in(db, IA_CALL), "Motivo-confidencial-9876"
    capt = login(client, CAPT_IA)
    put_review(client, capt, target, "met", reason=secret_reason)
    put_review(client, capt, target, "not_met", reason=secret_reason, expected_version=1)
    client.get(reviews_url(target), headers=capt)
    client.get(f"{reviews_url(target)}/{REF}/history", headers=capt)
    events = db.scalars(select(AuditEvent).where(AuditEvent.action.like("requirement_review.%")).order_by(AuditEvent.id)).all()
    assert [e.action for e in events] == ["requirement_review.created", "requirement_review.revised", "requirement_review.viewed", "requirement_review.history_viewed"]
    allowed_keys = {"codigo", "requirement_ref", "result", "from_result", "revision"}
    forbidden_text = [secret_reason, CAPT_IA, display_name(db, CAPT_IA)]
    for event in events:
        assert set(event.meta) <= allowed_keys
        assert not any(text in json.dumps(event.meta, ensure_ascii=False) for text in forbidden_text)
    assert events[1].meta["from_result"] == "met" and events[1].meta["revision"] == 2


def test_reason_free_text_is_only_returned_by_the_requirement_endpoints(client, db):
    """KAN-128 review R3: the reason must not leak into the dossier, CRM events, lists or the audit log."""
    target, secret_reason = application_in(db, IA_CALL), "Motivo-reservado-5521"
    admin = login(client, ADMIN)
    assert put_review(client, admin, target, "not_met", reason=secret_reason).status_code == 201
    for url in ("/api/v1/applications", f"/api/v1/applications/{target.id}", "/api/v1/audit-events"):
        r = client.get(url, headers=admin)
        assert r.status_code == 200, url
        assert secret_reason not in r.text, url
    assert secret_reason in client.get(reviews_url(target), headers=admin).text
    assert secret_reason not in client.get(f"/api/v1/applications/{target.id}", headers=login(client, SEL_IA)).text


BAD_ROWS = {
    "completed without author, date or reason": lambda author: {"result": "met"},
    "pending with a reason": lambda author: {"result": "pending", "reason": "No debe tener motivo"},
    "pending with an author": lambda author: {"result": "pending", "reviewer_user_id": author},
    "completed with a blank reason": lambda author: {"result": "met", "reviewer_user_id": author, "reviewed_at": utcnow(), "reason": "   "},
    "unknown result": lambda author: {"result": "unknown", "reviewer_user_id": author, "reviewed_at": utcnow(), "reason": "x"},
}


@pytest.mark.parametrize("case", list(BAD_ROWS))
def test_database_rejects_inconsistent_review_rows(db, case):
    target, author = application_in(db, IA_CALL), db.scalar(select(User))
    db.add(RequirementReview(application_id=target.id, requirement_ref=REF, **BAD_ROWS[case](author.id)))
    with pytest.raises(IntegrityError):
        db.flush()
    db.rollback()


def test_migration_0004_downgrades_without_touching_rag_tables_and_upgrades_again():
    cfg = Config(os.path.join(API_DIR, "alembic.ini"))
    cfg.set_main_option("script_location", os.path.join(API_DIR, "alembic"))
    review_tables = {"requirement_review", "requirement_review_revision"}
    try:
        command.downgrade(cfg, "0003")
        tables = set(inspect(engine).get_table_names())
        assert not review_tables & tables and {"knowledge_document", "knowledge_chunk"} <= tables
    finally:
        command.upgrade(cfg, "head")
    assert review_tables <= set(inspect(engine).get_table_names())
