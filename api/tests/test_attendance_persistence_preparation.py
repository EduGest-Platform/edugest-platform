"""Prepared policy and PostgreSQL SQL-shape checks; NO database is contacted."""

from datetime import date
from uuid import uuid4

import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateTable

import app.models  # noqa: F401 (resolve existing FK targets, no DDL)
from app.core.authz import Principal
from app.modules.catalog.models import Cohort
from app.modules.identity.models import RoleAssignment, User
from app.modules.learning.attendance_models import AttendanceRecord, AttendanceRevision, AttendanceSession
from app.modules.learning.attendance_policy import audit_metadata, can_write, require_any_attendance_write, validate_record_change, validate_session_creation
from app.modules.learning.attendance_repository import open_attendance_reader, record_query, session_query
from app.modules.learning.attendance_schemas import AttendanceRecordWrite, AttendanceSessionCreate
from app.modules.learning.attendance_service import AttendanceWriter
from tests.test_attendance_summary_contract import NOW, teacher


class NoDatabase:
    def __getattr__(self, name):
        raise AssertionError(f"No database operation is allowed in this test: {name}")


def body(**extra):
    base = {"status": "full_absence", "justified": False}
    if extra.get("expected_version") is not None:
        base["correction_reason"] = "Synthetic correction"
    return AttendanceRecordWrite(**(base | extra))


def staff(role, scope_type="global", scope_id=None):
    return Principal(User(id=uuid4(), is_active=True), [RoleAssignment(role=role, scope_type=scope_type, scope_id=scope_id)])


# PO decision 19/11/2026: the cohort teacher records and corrects; coordination and administration correct.
WRITE_RULES = [
    ("teacher of the cohort", lambda: teacher(), True, True),
    ("administration", lambda: staff("admin"), True, True),
    ("coordination", lambda: staff("coordinacion"), False, True),
    ("teacher of another cohort", lambda: teacher(cohort="COH-B"), False, False),
    ("captacion", lambda: staff("captacion", "program", "P-A"), False, False),
    ("seleccion", lambda: staff("seleccion"), False, False),
]


@pytest.mark.parametrize(("label", "make_actor", "may_record", "may_correct"), WRITE_RULES, ids=[r[0] for r in WRITE_RULES])
def test_write_permissions_come_from_the_configurable_permission_table(label, make_actor, may_record, may_correct):
    actor = make_actor()
    assert can_write(actor, "P-A", "COH-A", correction=False) is may_record
    assert can_write(actor, "P-A", "COH-A", correction=True) is may_correct


@pytest.mark.parametrize("case", ["revoked", "inactive", "learner"])
def test_revoked_inactive_and_learner_accounts_cannot_write(case):
    actor = teacher()
    if case == "revoked":
        actor.assignments[0].revoked_at = NOW
    if case == "inactive":
        actor.user.is_active = False
    if case == "learner":
        actor = Principal(User(id=uuid4(), person_id=uuid4(), is_active=True))
    assert not can_write(actor, "P-A", "COH-A", correction=True)
    with pytest.raises(HTTPException) as error:
        require_any_attendance_write(actor)
    assert error.value.status_code == 403


@pytest.mark.parametrize(("period", "existing"), [
    ("full_day", ["full_day"]), ("full_day", ["morning"]), ("full_day", ["afternoon"]),
    ("morning", ["full_day"]), ("afternoon", ["full_day"]), ("morning", ["morning"]),
])
def test_duplicate_or_overlapping_sessions_are_rejected(period, existing):
    cohort = Cohort(inicio=date(2026, 11, 1), fin=date(2026, 11, 30))
    with pytest.raises(HTTPException) as error:
        validate_session_creation(cohort, NOW.date(), period, existing)
    assert error.value.status_code == 409


def test_two_non_overlapping_half_sessions_are_allowed_within_cohort_dates():
    cohort = Cohort(inicio=date(2026, 11, 1), fin=date(2026, 11, 30))
    validate_session_creation(cohort, cohort.inicio, "morning", ["afternoon"])
    validate_session_creation(cohort, cohort.fin, "afternoon", ["morning"])
    with pytest.raises(HTTPException):
        validate_session_creation(cohort, date(2026, 12, 1), "morning", [])


@pytest.mark.parametrize("case", ["other_cohort", "future", "wrong_half", "missing_version", "stale_version", "version_on_create"])
def test_record_change_rejects_incompatible_scope_time_or_version(case):
    kwargs = dict(period="full_day", session_cohort_id="COH-A", enrollment_cohort_id="COH-A", enrollment_status="activa",
                  session_date=NOW.date(), today=NOW.date(), body=body(expected_version=1), current_version=1)
    if case == "other_cohort":
        kwargs["enrollment_cohort_id"] = "COH-B"
    if case == "future":
        kwargs["today"] = date(2026, 11, 18)
    if case == "wrong_half":
        kwargs["period"] = "morning"
    if case == "missing_version":
        kwargs["body"] = body()
    if case == "stale_version":
        kwargs["current_version"] = 2
    if case == "version_on_create":
        kwargs["current_version"] = None
    with pytest.raises(HTTPException):
        validate_record_change(**kwargs)


def test_first_record_and_current_version_correction_are_allowed():
    kwargs = dict(period="full_day", session_cohort_id="COH-A", enrollment_cohort_id="COH-A", enrollment_status="activa",
                  session_date=NOW.date(), today=NOW.date())
    validate_record_change(**kwargs, body=body(), current_version=None)
    validate_record_change(**kwargs, body=body(expected_version=3), current_version=3)


@pytest.mark.parametrize("status", ["baja_voluntaria", "finalizada"])
def test_no_new_attendance_after_withdrawal_but_corrections_stay_possible(status):
    """PO decision 19/11/2026: nothing new is recorded after a withdrawal; earlier records can still be corrected."""
    kwargs = dict(period="full_day", session_cohort_id="COH-A", enrollment_cohort_id="COH-A", enrollment_status=status,
                  session_date=NOW.date(), today=NOW.date())
    with pytest.raises(HTTPException) as error:
        validate_record_change(**kwargs, body=body(), current_version=None)
    assert error.value.status_code == 409
    validate_record_change(**kwargs, body=body(expected_version=1), current_version=1)


def test_reason_is_optional_on_first_record_and_required_on_correction():
    assert AttendanceRecordWrite(status="present", justified=False).correction_reason is None
    with pytest.raises(ValidationError):
        AttendanceRecordWrite(status="present", justified=False, expected_version=1)


def test_default_persistence_gates_prevent_any_database_use():
    writer = AttendanceWriter(NoDatabase())
    session_body = AttendanceSessionCreate(session_date=NOW.date(), period="full_day", modality="online")
    with pytest.raises(HTTPException) as error:
        writer.create_session(teacher(), "COH-A", session_body)
    assert error.value.status_code == 503
    with pytest.raises(HTTPException):
        writer.save_record(teacher(), uuid4(), uuid4(), body())
    with pytest.raises(HTTPException):
        with open_attendance_reader(NoDatabase()):
            pytest.fail("The reader must not be enabled by default")


def test_prepared_models_compile_as_postgresql_ddl_without_executing_it():
    for model in (AttendanceSession, AttendanceRecord, AttendanceRevision):
        ddl = str(CreateTable(model.__table__).compile(dialect=postgresql.dialect()))
        assert f"CREATE TABLE {model.__tablename__}" in ddl
    constraints = {c.name for c in AttendanceRecord.__table__.constraints}
    assert {"fk_attendance_record_session_cohort", "fk_attendance_record_enrollment_cohort", "uq_attendance_record_session_enrollment"} <= constraints
    assert "absence_days" not in AttendanceRecord.__table__.columns


def test_select_queries_are_scoped_and_parameterized():
    hostile = "COH-A' OR 1=1 --"
    query = session_query(hostile, date(2026, 11, 1), NOW.date()).compile(dialect=postgresql.dialect())
    assert hostile not in str(query) and hostile in query.params.values()
    assert "attendance_session.cohort_id =" in str(query)
    enrollment_id, session_id = uuid4(), uuid4()
    query = record_query(enrollment_id, [session_id]).compile(dialect=postgresql.dialect())
    assert str(query).lstrip().startswith("SELECT")
    assert "attendance_record.enrollment_id =" in str(query) and "attendance_record.session_id IN" in str(query)
    assert enrollment_id in query.params.values()
    assert "recorded_by_user_id" not in str(query) and "correction_reason" not in str(query)


def test_audit_metadata_excludes_status_reason_and_personal_content():
    data = audit_metadata(uuid4(), uuid4(), uuid4(), 2, NOW)
    assert set(data) == {"record_id", "session_id", "enrollment_id", "version", "recorded_at"}
    assert "correction_reason" not in data and "status" not in data
