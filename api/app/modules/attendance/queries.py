"""Shared attendance reads; authorization remains the caller's responsibility."""
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import UserFacingError
from app.modules.attendance.models import AttendanceRecord, AttendanceSession


def sessions_in(db: Session, cohort_id: str, date_from: date | None, date_to: date | None) -> list[AttendanceSession]:
    if date_from is not None and date_to is not None and date_from > date_to:
        raise UserFacingError(422, 'invalid_date_window', 'La fecha de inicio no puede ser posterior a la fecha de fin.')
    query = select(AttendanceSession).where(AttendanceSession.cohort_id == cohort_id)
    if date_from:
        query = query.where(AttendanceSession.session_date >= date_from)
    if date_to:
        query = query.where(AttendanceSession.session_date <= date_to)
    return list(db.scalars(query.order_by(AttendanceSession.session_date, AttendanceSession.shift)))


def records_of(db: Session, sessions: list[AttendanceSession]) -> list[AttendanceRecord]:
    ids = [session.id for session in sessions]
    return list(db.scalars(select(AttendanceRecord).where(AttendanceRecord.session_id.in_(ids)))) if ids else []
