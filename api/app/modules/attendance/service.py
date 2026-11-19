"""Attendance rules (KAN-55). Pure where possible so they can be tested and reused by the assistant tool."""

import uuid
from collections import defaultdict
from datetime import date, datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from fastapi import status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core import audit
from app.core.authz import Principal
from app.core.config import settings
from app.core.db import utcnow
from app.core.errors import UserFacingError
from app.modules.attendance.models import AttendanceRecord, AttendanceRecordRevision, AttendanceSession
from app.modules.attendance.schemas import CohortAttendance, EnrollmentAttendance, RecordWrite, SessionWrite
from app.modules.catalog.models import Cohort
from app.modules.learning.models import Enrollment

SHIFT_FRACTION = {"manana": Decimal("0.5"), "tarde": Decimal("0.5"), "completa": Decimal("1")}


ATTENDED = ("presente", "retraso")


def today_in(timezone: str) -> date:
    """Today's date on the cohort's own clock (Spain peninsula, Canary Islands or Portugal)."""
    return datetime.now(ZoneInfo(timezone)).date()


def is_held(session: AttendanceSession, timezone: str) -> bool:
    return session.session_date <= today_in(timezone)


def _conflict(code: str, message: str) -> UserFacingError:
    return UserFacingError(status.HTTP_409_CONFLICT, code, message)


# ---------- Sessions ----------


def _overlaps(db: Session, cohort_id: str, day: date, shift: str) -> bool:
    """A full day cannot coexist with a morning or afternoon of the same date (it would count the day twice)."""
    clashing = ("manana", "tarde") if shift == "completa" else ("completa",)
    query = select(AttendanceSession.id).where(
        AttendanceSession.cohort_id == cohort_id, AttendanceSession.session_date == day, AttendanceSession.shift.in_(clashing)
    )
    return db.scalar(query) is not None


def create_session(db: Session, p: Principal, cohort: Cohort, body: SessionWrite) -> AttendanceSession:
    if not cohort.inicio <= body.session_date <= cohort.fin:
        raise _conflict("session_outside_cohort", "La fecha está fuera de las fechas de la cohorte. Elige un día entre su inicio y su fin.")
    if _overlaps(db, cohort.id, body.session_date, body.shift):
        raise _conflict("session_overlaps", "Ese día ya tiene una sesión que se solapa (día completo frente a mañana o tarde). Revisa las sesiones del día.")
    session = AttendanceSession(
        cohort_id=cohort.id, session_date=body.session_date, shift=body.shift, duration_fraction=SHIFT_FRACTION[body.shift], created_by=p.user.id
    )
    db.add(session)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise _conflict("session_exists", "Esta sesión ya existe. Ábrela desde la lista de sesiones.") from None
    audit.record(db, p, "attendance.session_created", "attendance_session", str(session.id), cohort_id=cohort.id, shift=body.shift)
    db.commit()
    return session


# ---------- Records ----------


def _check_shape(body: RecordWrite) -> None:
    if body.status in ATTENDED and (body.modality is None or body.justification is not None):
        raise UserFacingError(422, "record_present_shape", "Si asistió (a tiempo o con retraso), indica si fue presencial u online y deja vacía la justificación.")
    if body.status == "ausente" and (body.justification is None or body.modality is not None):
        raise UserFacingError(422, "record_absent_shape", "Si está ausente, indica si la ausencia está justificada o no y deja vacía la modalidad.")


def _same_values(record: AttendanceRecord, body: RecordWrite) -> bool:
    return (record.status, record.modality, record.justification) == (body.status, body.modality, body.justification)


def _add_revision(db: Session, p: Principal, record: AttendanceRecord, reason: str | None) -> None:
    db.add(
        AttendanceRecordRevision(
            record_id=record.id, version=record.version, status=record.status, modality=record.modality,
            justification=record.justification, reason=reason, changed_by=p.user.id,
        )
    )


def save_record(db: Session, p: Principal, cohort: Cohort, session: AttendanceSession, enrollment: Enrollment, body: RecordWrite) -> AttendanceRecord:
    """First save registers attendance; later saves are corrections that need a reason and keep the previous version."""
    _check_shape(body)
    if enrollment.cohort_id != session.cohort_id:
        raise _conflict("enrollment_not_in_cohort", "Esta persona no está matriculada en la cohorte de la sesión.")
    if not is_held(session, cohort.timezone):
        raise _conflict("session_not_held", "La sesión aún no se ha celebrado. Podrás registrar la asistencia ese día.")
    query = select(AttendanceRecord).where(AttendanceRecord.session_id == session.id, AttendanceRecord.enrollment_id == enrollment.id)
    record = db.scalar(query.with_for_update())
    if record is None:
        return _register(db, p, session, enrollment, body)
    return _correct(db, p, record, body)


def _register(db: Session, p: Principal, session: AttendanceSession, enrollment: Enrollment, body: RecordWrite) -> AttendanceRecord:
    record = AttendanceRecord(
        session_id=session.id, enrollment_id=enrollment.id, status=body.status, modality=body.modality,
        justification=body.justification, version=1, recorded_by=p.user.id,
    )
    db.add(record)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise _conflict("record_exists", "Otra persona acaba de registrar esta asistencia. Recarga la sesión y corrígela si hace falta.") from None
    _add_revision(db, p, record, reason=None)
    audit.record(db, p, "attendance.recorded", "attendance_record", str(record.id), session_id=str(session.id), status=body.status)
    db.commit()
    return record


def _correct(db: Session, p: Principal, record: AttendanceRecord, body: RecordWrite) -> AttendanceRecord:
    if _same_values(record, body):
        return record
    if not body.reason:
        raise UserFacingError(422, "correction_reason_required", "Para corregir una asistencia ya registrada, escribe el motivo de la corrección.")
    previous = record.status
    record.status, record.modality, record.justification = body.status, body.modality, body.justification
    record.version += 1
    record.recorded_by, record.updated_at = p.user.id, utcnow()
    _add_revision(db, p, record, reason=body.reason)
    audit.record(
        db, p, "attendance.corrected", "attendance_record", str(record.id),
        session_id=str(record.session_id), version=record.version, from_status=previous, to_status=body.status,
    )
    db.commit()
    return record


# ---------- Summary ----------


def summarize(
    sessions: list[AttendanceSession], records: list[AttendanceRecord], enrollment_ids: list[uuid.UUID], timezone: str
) -> list[EnrollmentAttendance]:
    """Totals per enrollment over held sessions. Missing records count as "sin dato", never as absence."""
    held = [s for s in sessions if is_held(s, timezone)]
    by_key = {(r.session_id, r.enrollment_id): r for r in records}
    result = []
    for enrollment_id in enrollment_ids:
        totals: dict[str, Decimal] = defaultdict(Decimal)
        for session in held:
            fraction = session.duration_fraction
            totals["held"] += fraction
            record = by_key.get((session.id, enrollment_id))
            if record is None:
                totals["unrecorded"] += fraction
            elif record.status in ATTENDED:
                totals[f"attended_{record.modality}"] += fraction
                if record.status == "retraso":
                    totals["late"] += fraction
            else:
                totals[record.justification] += fraction
        result.append(_to_out(enrollment_id, totals))
    return result


def _rate(attended: float, recorded: float) -> float | None:
    return round(attended / recorded, 4) if recorded else None


def _to_out(enrollment_id: uuid.UUID, t: dict[str, Decimal]) -> EnrollmentAttendance:
    attended = t["attended_presencial"] + t["attended_online"]
    recorded = attended + t["justificada"] + t["no_justificada"]
    return EnrollmentAttendance(
        enrollment_id=enrollment_id,
        held_days=float(t["held"]),
        attended_days=float(attended),
        late_days=float(t["late"]),
        attended_in_person_days=float(t["attended_presencial"]),
        attended_online_days=float(t["attended_online"]),
        justified_absence_days=float(t["justificada"]),
        unjustified_absence_days=float(t["no_justificada"]),
        unrecorded_days=float(t["unrecorded"]),
        attendance_rate=_rate(float(attended), float(recorded)),
    )


def cohort_totals(items: list[EnrollmentAttendance]) -> CohortAttendance:
    """Aggregate for coordination. Hidden below the minimum group size so no one can be singled out."""
    if len(items) < settings.min_group_size:
        return CohortAttendance(enrollments=None, suppressed=True, min_group_size=settings.min_group_size)

    def total(field: str) -> float:
        return sum(getattr(item, field) for item in items)

    recorded = total("attended_days") + total("justified_absence_days") + total("unjustified_absence_days")
    return CohortAttendance(
        enrollments=len(items), suppressed=False, min_group_size=settings.min_group_size,
        attended_days=total("attended_days"), late_days=total("late_days"),
        justified_absence_days=total("justified_absence_days"), unjustified_absence_days=total("unjustified_absence_days"),
        unrecorded_days=total("unrecorded_days"), attendance_rate=_rate(total("attended_days"), recorded),
    )
