"""Schema-independent contract checks; fixture source is explicitly synthetic."""

from dataclasses import replace
from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.core.authz import Principal
from app.modules.identity.models import RoleAssignment, User
from app.modules.learning.attendance_schemas import AttendanceRecordWrite
from app.modules.learning.attendance_summary import EnrollmentContext, RecordSnapshot, SessionSnapshot, get_attendance_summary

NOW = datetime(2026, 11, 19, 12, tzinfo=timezone.utc)
START, END = date(2026, 11, 16), date(2026, 11, 22)


class SyntheticReader:
    source = "synthetic_fixture"

    def __init__(self):
        self.context = EnrollmentContext(uuid4(), uuid4(), "COH-A", "P-A")
        self.session_rows = []
        self.record_rows = []
        self.calls = []

    def enrollment_context(self, enrollment_id):
        self.calls.append("context")
        return self.context if enrollment_id == self.context.enrollment_id else None

    def sessions(self, cohort_id, date_from, date_to):
        self.calls.append("sessions")
        return [s for s in self.session_rows if date_from <= s.session_date <= date_to and s.cohort_id == cohort_id]

    def records(self, enrollment_id, session_ids):
        self.calls.append("records")
        return [r for r in self.record_rows if r.enrollment_id == enrollment_id and r.session_id in session_ids]


def teacher(cohort="COH-A", role="docente", scope_type="cohort"):
    return Principal(User(id=uuid4(), is_active=True), [RoleAssignment(role=role, scope_type=scope_type, scope_id=cohort)])


def summary(reader, actor=None, **overrides):
    return get_attendance_summary(reader, actor or teacher(), reader.context.enrollment_id,
                                  overrides.get("date_from", START), overrides.get("date_to", END), as_of=overrides.get("as_of", NOW))


def add_record(reader, day, status, justified=False, period="full_day"):
    session = SessionSnapshot(uuid4(), reader.context.cohort_id, date(2026, 11, day), period)
    reader.session_rows.append(session)
    reader.record_rows.append(RecordSnapshot(session.id, reader.context.enrollment_id, status, justified, NOW))


def test_summary_counts_weighted_absences_and_unknown_separately():
    reader = SyntheticReader()
    add_record(reader, 16, "full_absence")
    add_record(reader, 17, "morning_absence", justified=True)
    add_record(reader, 18, "present")
    reader.session_rows.append(SessionSnapshot(uuid4(), "COH-A", date(2026, 11, 19), "full_day"))
    result = summary(reader)
    assert result.recorded_absence_days == Decimal("1.5")
    assert result.justified_absence_days == Decimal("0.5")
    assert result.unjustified_absence_days == Decimal("1")
    assert result.unknown_days == Decimal("1") and result.recorded_days == Decimal("3")
    assert result.data_state == "partial" and result.unrecorded_sessions == 1
    assert result.source == "synthetic_fixture" and result.latest_recorded_at == NOW


@pytest.mark.parametrize("with_session", [False, True])
def test_no_record_returns_unknown_not_zero(with_session):
    reader = SyntheticReader()
    if with_session:
        reader.session_rows.append(SessionSnapshot(uuid4(), "COH-A", START, "morning"))
    result = summary(reader)
    assert result.data_state == "no_data"
    assert result.recorded_absence_days is None
    assert result.justified_absence_days is None and result.unjustified_absence_days is None
    assert result.unknown_days == (Decimal("0.5") if with_session else Decimal("0"))


def test_explicit_presence_can_report_zero_with_complete_coverage():
    reader = SyntheticReader()
    add_record(reader, 16, "present")
    result = summary(reader)
    assert result.recorded_absence_days == 0 and result.data_state == "complete"


def test_half_sessions_do_not_double_count_day():
    reader = SyntheticReader()
    add_record(reader, 16, "morning_absence", period="morning")
    add_record(reader, 16, "present", period="afternoon")
    result = summary(reader)
    assert result.scheduled_days == 1 and result.recorded_absence_days == Decimal("0.5")


def test_future_sessions_and_future_records_are_not_counted_as_attendance():
    reader = SyntheticReader()
    add_record(reader, 20, "full_absence")
    add_record(reader, 16, "full_absence")
    reader.record_rows[-1] = replace(reader.record_rows[-1], recorded_at=datetime(2026, 11, 20, tzinfo=timezone.utc))
    result = summary(reader)
    assert result.held_sessions == 1 and result.recorded_sessions == 0
    assert result.recorded_absence_days is None and result.unknown_days == 1


def test_period_is_inclusive_and_not_replaced_by_default_dates():
    reader = SyntheticReader()
    add_record(reader, 16, "full_absence")
    add_record(reader, 17, "present")
    result = summary(reader, date_from=date(2026, 11, 17), date_to=date(2026, 11, 17))
    assert result.held_sessions == 1 and result.recorded_absence_days == 0
    assert result.date_from == result.date_to == date(2026, 11, 17)


@pytest.mark.parametrize("role", ["captacion", "seleccion"])
def test_admissions_roles_have_no_attendance_access_and_are_stopped_before_any_lookup(role):
    reader = SyntheticReader()
    with pytest.raises(HTTPException) as error:
        summary(reader, teacher(role=role, scope_type="global"))
    assert error.value.status_code == 403
    assert reader.calls == []


def test_coordination_reads_attendance_per_po_decision():
    reader = SyntheticReader()
    assert summary(reader, teacher(role="coordinacion", scope_type="global")).cohort_id == "COH-A"


@pytest.mark.parametrize("case", ["wrong_cohort", "person_without_enrollment"])
def test_out_of_scope_access_is_an_explained_403_audited_before_attendance_queries(case):
    reader, actor = SyntheticReader(), teacher()
    if case == "wrong_cohort":
        actor.assignments[0].scope_id = "COH-B"
    if case == "person_without_enrollment":
        actor = Principal(User(id=uuid4(), person_id=uuid4(), is_active=True))
    denied = []
    with pytest.raises(HTTPException) as error:
        get_attendance_summary(reader, actor, reader.context.enrollment_id, START, END, as_of=NOW, on_denied=denied.append)
    assert error.value.status_code == 403 and "administración" in error.value.detail
    assert denied == [reader.context]
    assert reader.calls == ["context"]


@pytest.mark.parametrize("case", ["revoked", "inactive"])
def test_revoked_or_inactive_staff_are_stopped_before_any_lookup(case):
    reader, actor = SyntheticReader(), teacher()
    if case == "revoked":
        actor.assignments[0].revoked_at = NOW
    if case == "inactive":
        actor.user.is_active = False
    with pytest.raises(HTTPException) as error:
        summary(reader, actor)
    assert error.value.status_code == 403
    assert reader.calls == []


def test_program_scoped_teacher_reaches_the_cohorts_of_that_program():
    """Scopes follow the shared permission model: a program-level assignment covers its cohorts."""
    reader = SyntheticReader()
    assert summary(reader, teacher(cohort="P-A", scope_type="program")).cohort_id == "COH-A"


def test_person_can_read_only_own_enrollment():
    reader = SyntheticReader()
    actor = Principal(User(id=uuid4(), person_id=reader.context.person_id, is_active=True))
    assert summary(reader, actor).enrollment_id == reader.context.enrollment_id
    other = replace(reader.context, person_id=uuid4())
    reader.context = other
    reader.calls.clear()
    with pytest.raises(HTTPException):
        summary(reader, actor)
    assert reader.calls == ["context"]


def test_administrator_read_still_respects_assignment_scope():
    reader = SyntheticReader()
    assert summary(reader, teacher(role="admin")).cohort_id == "COH-A"
    with pytest.raises(HTTPException):
        summary(reader, teacher(cohort="COH-B", role="admin"))


@pytest.mark.parametrize("case", ["duplicate_session", "overlapping_session", "duplicate_record", "incompatible_status"])
def test_bad_repository_data_cannot_inflate_totals(case):
    reader = SyntheticReader()
    add_record(reader, 16, "present")
    if case == "duplicate_session":
        reader.session_rows.append(reader.session_rows[0])
    if case == "overlapping_session":
        reader.session_rows.append(SessionSnapshot(uuid4(), "COH-A", START, "morning"))
    if case == "duplicate_record":
        reader.record_rows.append(reader.record_rows[0])
    if case == "incompatible_status":
        reader.session_rows[0] = replace(reader.session_rows[0], period="afternoon")
        reader.record_rows[0] = replace(reader.record_rows[0], status="morning_absence")
    with pytest.raises(ValueError):
        summary(reader)


def test_invalid_period_and_naive_cutoff_are_rejected():
    reader = SyntheticReader()
    with pytest.raises(HTTPException):
        summary(reader, date_from=END, date_to=START)
    with pytest.raises(ValueError):
        summary(reader, as_of=NOW.replace(tzinfo=None))
    assert not reader.calls


def test_summary_contains_no_correction_reason_identity_or_database_details():
    result = summary(SyntheticReader()).model_dump_json()
    for field in ("correction_reason", "person_id", "display_name", "email", "database_url", "sql"):
        assert f'"{field}"' not in result


@pytest.mark.parametrize("extra", [{"recorded_by_user_id": str(uuid4())}, {"recorded_at": NOW.isoformat()}, {"expected_version": True}, {"status": "present", "justified": True}])
def test_write_contract_rejects_forged_server_fields(extra):
    body = {"status": "full_absence", "justified": False}
    with pytest.raises(ValidationError):
        AttendanceRecordWrite(**(body | extra))
