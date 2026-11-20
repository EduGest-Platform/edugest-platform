"""Prepared PostgreSQL SELECT adapter; disabled until schema integration approval."""

from collections.abc import Iterator
from contextlib import contextmanager
from datetime import date
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import Engine, select, text
from sqlalchemy.orm import Session

from app.modules.catalog.models import Cohort
from app.modules.learning.attendance_models import AttendanceRecord, AttendanceSession
from app.modules.learning.attendance_summary import EnrollmentContext, RecordSnapshot, SessionSnapshot
from app.modules.learning.models import Enrollment


def session_query(cohort_id: str, date_from: date, date_to: date):
    return select(AttendanceSession.id, AttendanceSession.cohort_id, AttendanceSession.session_date, AttendanceSession.period).where(
        AttendanceSession.cohort_id == cohort_id,
        AttendanceSession.session_date >= date_from, AttendanceSession.session_date <= date_to,
    ).order_by(AttendanceSession.session_date, AttendanceSession.period)


def record_query(enrollment_id: UUID, session_ids: list[UUID]):
    return select(AttendanceRecord.session_id, AttendanceRecord.enrollment_id, AttendanceRecord.status,
                  AttendanceRecord.justified, AttendanceRecord.recorded_at).where(
        AttendanceRecord.enrollment_id == enrollment_id, AttendanceRecord.session_id.in_(session_ids),
    )


class PostgresAttendanceReader:
    source = "postgresql"

    def __init__(self, session: Session):
        self._session = session

    def enrollment_context(self, enrollment_id: UUID) -> EnrollmentContext | None:
        row = self._session.execute(
            select(Enrollment.id, Enrollment.person_id, Enrollment.cohort_id, Cohort.program_id)
            .join(Cohort, Cohort.id == Enrollment.cohort_id).where(Enrollment.id == enrollment_id)
        ).first()
        return EnrollmentContext(*row) if row else None

    def sessions(self, cohort_id: str, date_from: date, date_to: date) -> list[SessionSnapshot]:
        return [SessionSnapshot(*row) for row in self._session.execute(session_query(cohort_id, date_from, date_to))]

    def records(self, enrollment_id: UUID, session_ids: list[UUID]) -> list[RecordSnapshot]:
        if not session_ids:
            return []
        return [RecordSnapshot(*row) for row in self._session.execute(record_query(enrollment_id, session_ids))]


@contextmanager
def open_attendance_reader(engine: Engine, *, schema_enabled: bool = False) -> Iterator[PostgresAttendanceReader]:
    if not schema_enabled:
        raise HTTPException(503, "La persistencia académica está pendiente de habilitar")
    # Separate connection: authentication may already have opened a transaction.
    with engine.connect().execution_options(isolation_level="REPEATABLE READ") as connection:
        with connection.begin():
            connection.execute(text("SET TRANSACTION READ ONLY"))
            with Session(bind=connection) as session:
                yield PostgresAttendanceReader(session)
