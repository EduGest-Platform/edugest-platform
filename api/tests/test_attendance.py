"""KAN-55: attendance 1 / 0.5, justified vs unjustified, "sin dato", audited corrections and cohort scope."""

from datetime import timedelta

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.exc import DBAPIError

from app.core.db import utcnow
from app.modules.attendance.models import AttendanceRecordRevision, AttendanceSession
from app.modules.audit.models import AuditEvent
from app.modules.catalog.models import Cohort
from app.modules.identity.models import RoleAssignment, User
from app.modules.learning.models import Enrollment
from tests.conftest import ADMIN, CAPT_IA, CODER, COORD, DOCENTE, login

COHORT = "COH-IA"
OTHER = "COH-DATA"
PRESENT = {"status": "presente", "modality": "presencial"}
ONLINE = {"status": "presente", "modality": "online"}
UNJUSTIFIED = {"status": "ausente", "justification": "no_justificada"}
JUSTIFIED = {"status": "ausente", "justification": "justificada"}


@pytest.fixture
def teacher(client):
    return login(client, DOCENTE)


@pytest.fixture(autouse=True)
def _cohorts_cover_today(db):
    """Seed cohort dates are fixed; widen them so sessions in the past and future are valid whenever tests run."""
    today = utcnow().date()
    for cohort in db.scalars(select(Cohort)):
        cohort.inicio, cohort.fin = today - timedelta(days=60), today + timedelta(days=60)
    db.commit()


def enrollment_of(db, cohort_id=COHORT) -> str:
    return str(db.scalar(select(Enrollment.id).where(Enrollment.cohort_id == cohort_id).order_by(Enrollment.created_at, Enrollment.id)))


def day(offset: int) -> str:
    return (utcnow().date() + timedelta(days=offset)).isoformat()


def new_session(client, headers, offset=-1, shift="completa", cohort=COHORT):
    r = client.post(f"/api/v1/cohorts/{cohort}/attendance-sessions", json={"session_date": day(offset), "shift": shift}, headers=headers)
    assert r.status_code == 201, r.text
    return r.json()


def put(client, headers, session_id, enrollment_id, body):
    return client.put(f"/api/v1/attendance-sessions/{session_id}/records/{enrollment_id}", json=body, headers=headers)


def summary(client, headers, enrollment_id, cohort=COHORT):
    r = client.get(f"/api/v1/cohorts/{cohort}/attendance-summary", params={"enrollment_id": enrollment_id}, headers=headers)
    assert r.status_code == 200, r.text
    return r.json()["items"][0]


# ---------- Sessions ----------


def test_shift_sets_the_weight_full_day_1_half_day_half(client, teacher):
    assert new_session(client, teacher, shift="completa")["duration_fraction"] == 1
    assert new_session(client, teacher, offset=-2, shift="manana")["duration_fraction"] == 0.5
    assert new_session(client, teacher, offset=-2, shift="tarde")["duration_fraction"] == 0.5


def test_duplicate_and_overlapping_sessions_are_rejected(client, teacher):
    new_session(client, teacher, offset=-1, shift="completa")
    again = client.post(f"/api/v1/cohorts/{COHORT}/attendance-sessions", json={"session_date": day(-1), "shift": "completa"}, headers=teacher)
    half = client.post(f"/api/v1/cohorts/{COHORT}/attendance-sessions", json={"session_date": day(-1), "shift": "manana"}, headers=teacher)
    assert again.status_code == 409 and again.json()["code"] == "session_exists"
    assert half.status_code == 409 and half.json()["code"] == "session_overlaps"


def test_session_outside_cohort_dates_is_rejected(client, teacher):
    r = client.post(f"/api/v1/cohorts/{COHORT}/attendance-sessions", json={"session_date": day(365), "shift": "manana"}, headers=teacher)
    assert r.status_code == 409 and r.json()["code"] == "session_outside_cohort"


def test_database_rejects_a_weight_that_does_not_match_the_shift(db):
    teacher_id = db.scalar(select(User.id).where(User.email == DOCENTE))
    db.add(AttendanceSession(cohort_id=COHORT, session_date=utcnow().date(), shift="manana", duration_fraction=1, created_by=teacher_id))
    with pytest.raises(DBAPIError):
        db.commit()
    db.rollback()


# ---------- Records and totals ----------


def test_totals_add_full_and_half_days_and_keep_justified_apart(client, db, teacher):
    enrollment = enrollment_of(db)
    plan = [(-5, "completa", PRESENT), (-4, "manana", ONLINE), (-4, "tarde", UNJUSTIFIED), (-3, "completa", JUSTIFIED), (-2, "manana", None)]
    for offset, shift, body in plan:
        session = new_session(client, teacher, offset=offset, shift=shift)
        if body:
            assert put(client, teacher, session["id"], enrollment, body).status_code == 200
    totals = summary(client, teacher, enrollment)
    assert totals["held_days"] == 3.5
    assert totals["present_days"] == 1.5 and totals["present_in_person_days"] == 1 and totals["present_online_days"] == 0.5
    assert totals["unjustified_absence_days"] == 0.5
    assert totals["justified_absence_days"] == 1
    assert totals["unrecorded_days"] == 0.5  # held morning without a record: "sin dato", not an absence
    assert totals["attendance_rate"] == 0.5  # 1.5 present / 3 recorded


def test_no_records_means_no_rate_never_zero_attendance(client, db, teacher):
    new_session(client, teacher, offset=-1)
    totals = summary(client, teacher, enrollment_of(db))
    assert totals["unrecorded_days"] == 1 and totals["attendance_rate"] is None
    assert totals["unjustified_absence_days"] == 0 and totals["justified_absence_days"] == 0


def test_future_sessions_do_not_count_and_cannot_be_recorded(client, db, teacher):
    future = new_session(client, teacher, offset=3)
    r = put(client, teacher, future["id"], enrollment_of(db), PRESENT)
    assert r.status_code == 409 and r.json()["code"] == "session_not_held"
    assert summary(client, teacher, enrollment_of(db))["held_days"] == 0


@pytest.mark.parametrize(
    "body",
    [{"status": "presente"}, {"status": "presente", "modality": "online", "justification": "justificada"}, {"status": "ausente"}, {"status": "ausente", "justification": "justificada", "modality": "online"}],
)
def test_incoherent_records_are_rejected(client, db, teacher, body):
    session = new_session(client, teacher)
    assert put(client, teacher, session["id"], enrollment_of(db), body).status_code == 422


def test_enrollment_from_another_cohort_cannot_be_recorded(client, db, teacher):
    session = new_session(client, teacher)
    r = put(client, teacher, session["id"], enrollment_of(db, OTHER), PRESENT)
    assert r.status_code == 409 and r.json()["code"] == "enrollment_not_in_cohort"


# ---------- Corrections ----------


def test_correction_needs_a_reason_and_keeps_every_version(client, db, teacher):
    session, enrollment = new_session(client, teacher), enrollment_of(db)
    first = put(client, teacher, session["id"], enrollment, UNJUSTIFIED).json()
    assert put(client, teacher, session["id"], enrollment, JUSTIFIED).json()["code"] == "correction_reason_required"
    fixed = put(client, teacher, session["id"], enrollment, {**JUSTIFIED, "reason": "Justificante entregado en secretaría"})
    assert fixed.status_code == 200 and fixed.json()["version"] == 2
    history = client.get(f"/api/v1/attendance-records/{first['id']}/revisions", headers=teacher).json()["items"]
    assert [(h["version"], h["justification"], h["reason"]) for h in history] == [
        (1, "no_justificada", None),
        (2, "justificada", "Justificante entregado en secretaría"),
    ]
    assert history[1]["changed_by"] == "Docente demo"
    audit = db.scalar(select(AuditEvent).where(AuditEvent.action == "attendance.corrected"))
    assert audit.meta["from_status"] == "ausente" and "reason" not in audit.meta  # free text never goes to the audit log


def test_saving_the_same_values_again_is_not_a_correction(client, db, teacher):
    session, enrollment = new_session(client, teacher), enrollment_of(db)
    put(client, teacher, session["id"], enrollment, PRESENT)
    again = put(client, teacher, session["id"], enrollment, PRESENT)
    assert again.status_code == 200 and again.json()["version"] == 1


def test_revision_history_cannot_be_edited_or_deleted(client, db, teacher):
    session = new_session(client, teacher)
    put(client, teacher, session["id"], enrollment_of(db), PRESENT)
    revision_id = db.scalar(select(AttendanceRecordRevision.id))
    for statement in ("UPDATE attendance_record_revision SET status = 'ausente' WHERE id = :id", "DELETE FROM attendance_record_revision WHERE id = :id"):
        with pytest.raises(DBAPIError):
            db.execute(text(statement), {"id": revision_id})
        db.rollback()
    assert db.scalar(select(func.count()).select_from(AttendanceRecordRevision)) == 1


# ---------- Permissions ----------


def test_teacher_of_another_cohort_gets_403(client, db):
    teacher_id = db.scalar(select(User.id).where(User.email == DOCENTE))
    db.query(RoleAssignment).filter(RoleAssignment.user_id == teacher_id, RoleAssignment.scope_id == COHORT).delete()
    db.commit()
    headers = login(client, DOCENTE)  # now only teaches COH-DATA
    r = client.post(f"/api/v1/cohorts/{COHORT}/attendance-sessions", json={"session_date": day(-1), "shift": "manana"}, headers=headers)
    assert r.status_code == 403
    assert client.get(f"/api/v1/cohorts/{COHORT}/attendance-summary", headers=headers).status_code == 403


@pytest.mark.parametrize("email", [CAPT_IA, COORD, CODER])
def test_non_teaching_roles_cannot_record_or_read_attendance(client, email):
    headers = login(client, email)
    assert client.post(f"/api/v1/cohorts/{COHORT}/attendance-sessions", json={"session_date": day(-1), "shift": "manana"}, headers=headers).status_code == 403
    assert client.get(f"/api/v1/cohorts/{COHORT}/attendance-sessions", headers=headers).status_code == 403


def test_admin_can_read_and_anonymous_gets_401(client):
    assert client.get(f"/api/v1/cohorts/{COHORT}/attendance-summary", headers=login(client, ADMIN)).status_code == 200
    assert client.get(f"/api/v1/cohorts/{COHORT}/attendance-summary").status_code == 401
