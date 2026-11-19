"""Prepared academic attendance policy. Permissions live in ROLE_PERMISSIONS (configurable), never in role names."""

from datetime import date, datetime
from uuid import UUID

from fastapi import HTTPException

from app.core.authz import ATTENDANCE_CORRECT, ATTENDANCE_READ, ATTENDANCE_RECORD, Principal, Scope
from app.modules.catalog.models import Cohort
from app.modules.learning.attendance_schemas import PERIOD_STATUSES, AttendanceRecordWrite

OUT_OF_SCOPE_MESSAGE = (
    "Esta matrícula o cohorte no está entre las que tienes asignadas. "
    "Si necesitas acceso, pídeselo a administración."
)


def effective_principal(actor: Principal) -> Principal:
    """Only active users and non-revoked assignments count (sessions already filter them; this is defence in depth)."""
    if not actor.user.is_active:
        return Principal(actor.user, [])
    return Principal(actor.user, [a for a in actor.assignments if a.revoked_at is None])


def holds_anywhere(actor: Principal, *permissions: str) -> bool:
    """True when the actor holds any of the permissions in at least one scope (used to answer 403 before lookups)."""
    effective = effective_principal(actor)
    return any(effective._grants(a, perm) for a in effective.assignments for perm in permissions)


def can_on_cohort(actor: Principal, permission: str, program_id: str, cohort_id: str) -> bool:
    return effective_principal(actor).can(permission, Scope(program_id=program_id, cohort_id=cohort_id))


def can_write(actor: Principal, program_id: str, cohort_id: str, *, correction: bool) -> bool:
    """Recording needs attendance.record; correcting an existing record also accepts attendance.correct."""
    if can_on_cohort(actor, ATTENDANCE_RECORD, program_id, cohort_id):
        return True
    return correction and can_on_cohort(actor, ATTENDANCE_CORRECT, program_id, cohort_id)


def can_read(actor: Principal, program_id: str, cohort_id: str) -> bool:
    return can_on_cohort(actor, ATTENDANCE_READ, program_id, cohort_id)


def require_any_attendance_write(actor: Principal) -> None:
    if not holds_anywhere(actor, ATTENDANCE_RECORD, ATTENDANCE_CORRECT):
        raise HTTPException(403, "No tienes permiso para registrar ni corregir asistencia")


def out_of_scope() -> HTTPException:
    return HTTPException(403, OUT_OF_SCOPE_MESSAGE)


def validate_session_creation(
    cohort: Cohort, session_date: date, period: str, existing_periods: list[str],
) -> None:
    if not cohort.inicio <= session_date <= cohort.fin:
        raise HTTPException(422, "La sesión debe estar dentro de las fechas de la cohorte")
    if period in existing_periods or (existing_periods and "full_day" in {*existing_periods, period}):
        raise HTTPException(409, "Ya existe una sesión para esa franja o una sesión que se solapa")


def validate_record_change(
    *, period: str, session_cohort_id: str, enrollment_cohort_id: str, enrollment_status: str,
    session_date: date, today: date, body: AttendanceRecordWrite, current_version: int | None,
) -> None:
    if session_cohort_id != enrollment_cohort_id:
        raise HTTPException(404, "Matrícula no encontrada en esta cohorte")
    if session_date > today:
        raise HTTPException(409, "La sesión aún no se ha celebrado")
    if body.status not in PERIOD_STATUSES[period]:
        raise HTTPException(422, "La ausencia no corresponde a la franja de la sesión")
    if body.expected_version != current_version:
        raise HTTPException(409, "El registro ha cambiado: vuelve a cargarlo antes de corregirlo")
    if current_version is None and enrollment_status != "activa":
        # PO decision 19/11/2026: no new attendance after a withdrawal or the end of the enrollment.
        # Corrections of records taken while it was active stay possible, with a reason and audit.
        raise HTTPException(409, "La matrícula no está activa (baja o finalizada): no se registra nueva asistencia")


def audit_metadata(record_id: UUID, session_id: UUID, enrollment_id: UUID, version: int, recorded_at: datetime) -> dict:
    """No justification text, personal identifiers, status or correction reason."""
    return {
        "record_id": str(record_id), "session_id": str(session_id),
        "enrollment_id": str(enrollment_id), "version": version, "recorded_at": recorded_at.isoformat(),
    }
