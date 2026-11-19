"""Allowlisted read-only service; authorization precedes attendance retrieval.

The repository is injected by the backend, never selected by the language model.
No SQL, database URL, correction text or health detail enters the DTO.
"""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Literal, Protocol
from uuid import UUID
from zoneinfo import ZoneInfo

from fastapi import HTTPException

from app.core.authz import ATTENDANCE_READ, Principal
from app.modules.learning.attendance_policy import can_read, holds_anywhere, out_of_scope
from app.modules.learning.attendance_schemas import ABSENCE_DAYS, PERIOD_DURATION, PERIOD_STATUSES, AttendanceSummary


@dataclass(frozen=True)
class EnrollmentContext:
    enrollment_id: UUID
    person_id: UUID
    cohort_id: str
    program_id: str


@dataclass(frozen=True)
class SessionSnapshot:
    id: UUID
    cohort_id: str
    session_date: date
    period: Literal["full_day", "morning", "afternoon"]


@dataclass(frozen=True)
class RecordSnapshot:
    session_id: UUID
    enrollment_id: UUID
    status: Literal["present", "full_absence", "morning_absence", "afternoon_absence"]
    justified: bool
    recorded_at: datetime


class AttendanceReader(Protocol):
    source: Literal["postgresql", "synthetic_fixture"]

    def enrollment_context(self, enrollment_id: UUID) -> EnrollmentContext | None: ...
    def sessions(self, cohort_id: str, date_from: date, date_to: date) -> list[SessionSnapshot]: ...
    def records(self, enrollment_id: UUID, session_ids: list[UUID]) -> list[RecordSnapshot]: ...


def require_attendance_reader_anywhere(actor: Principal) -> None:
    """Before any lookup: staff need attendance.read somewhere; a learner may only read their own enrollment."""
    if not actor.user.is_active:
        raise HTTPException(403, "No tienes permiso para consultar asistencia")
    if actor.user.person_id is None and not holds_anywhere(actor, ATTENDANCE_READ):
        raise HTTPException(403, "No tienes permiso para consultar asistencia")


def require_attendance_reader(actor: Principal, context: EnrollmentContext) -> None:
    if actor.user.person_id is not None and actor.user.person_id == context.person_id:
        return
    if can_read(actor, context.program_id, context.cohort_id):
        return
    # PO decision 19/11/2026: out of scope is an explained 403 (and audited by the caller), not a hidden 404.
    raise out_of_scope()


def get_attendance_summary(
    reader: AttendanceReader, actor: Principal, enrollment_id: UUID,
    date_from: date, date_to: date, *, as_of: datetime,
    on_denied: Callable[[EnrollmentContext], None] | None = None,
) -> AttendanceSummary:
    """`on_denied` lets the backend audit an out-of-scope attempt (ids only) before the 403 is returned."""
    if date_from > date_to:
        raise HTTPException(422, "La fecha inicial no puede ser posterior a la final")
    if as_of.tzinfo is None or as_of.utcoffset() is None:
        raise ValueError("The backend cutoff must be timezone-aware")
    require_attendance_reader_anywhere(actor)
    context = reader.enrollment_context(enrollment_id)
    if context is None:
        raise HTTPException(404, "Matrícula no encontrada")
    try:
        require_attendance_reader(actor, context)
    except HTTPException:
        if on_denied is not None:
            on_denied(context)
        raise
    today = as_of.astimezone(ZoneInfo("Europe/Madrid")).date()
    sessions = reader.sessions(context.cohort_id, date_from, min(date_to, today)) if date_from <= today else []
    session_by_id = {}
    occupied_periods: dict[date, set[str]] = {}
    for session in sessions:
        if session.cohort_id != context.cohort_id or not date_from <= session.session_date <= min(date_to, today):
            raise ValueError("Attendance repository returned an out-of-scope session")
        periods = occupied_periods.setdefault(session.session_date, set())
        if session.id in session_by_id or session.period in periods or (periods and "full_day" in periods | {session.period}):
            raise ValueError("Attendance repository returned duplicate or overlapping sessions")
        periods.add(session.period)
        session_by_id[session.id] = session
    records = reader.records(enrollment_id, list(session_by_id)) if sessions else []
    recorded = {}
    for record in records:
        if record.enrollment_id != enrollment_id or record.session_id not in session_by_id:
            raise ValueError("Attendance repository returned an out-of-scope record")
        if record.recorded_at.tzinfo is None or record.recorded_at.utcoffset() is None:
            raise ValueError("Record timestamp must be timezone-aware")
        if record.recorded_at > as_of:
            continue
        if record.session_id in recorded:
            raise ValueError("Attendance repository returned duplicate records")
        if record.status not in PERIOD_STATUSES[session_by_id[record.session_id].period]:
            raise ValueError("Attendance status is incompatible with the session period")
        if record.status == "present" and record.justified:
            raise ValueError("Presence cannot be a justified absence")
        recorded[record.session_id] = record
    scheduled_days = sum((PERIOD_DURATION[s.period] for s in sessions), Decimal("0"))
    recorded_days = sum((PERIOD_DURATION[session_by_id[sid].period] for sid in recorded), Decimal("0"))
    total = sum((ABSENCE_DAYS[r.status] for r in recorded.values()), Decimal("0")) if recorded else None
    justified = sum((ABSENCE_DAYS[r.status] for r in recorded.values() if r.justified), Decimal("0")) if recorded else None
    unjustified = total - justified if recorded else None
    return AttendanceSummary(
        enrollment_id=enrollment_id, cohort_id=context.cohort_id, date_from=date_from, date_to=date_to,
        as_of=as_of, source=reader.source, data_state="no_data" if not recorded else "complete" if len(recorded) == len(sessions) else "partial",
        held_sessions=len(sessions), recorded_sessions=len(recorded), unrecorded_sessions=len(sessions) - len(recorded),
        scheduled_days=scheduled_days, recorded_days=recorded_days, unknown_days=scheduled_days - recorded_days,
        recorded_absence_days=total, justified_absence_days=justified, unjustified_absence_days=unjustified,
        latest_recorded_at=max((r.recorded_at for r in recorded.values()), default=None),
    )
