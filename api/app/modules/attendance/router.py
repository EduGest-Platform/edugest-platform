import uuid
from datetime import date

from fastapi import APIRouter, Path, Query, status
from sqlalchemy import select

from app.core import audit
from app.core.deps import DB, CurrentPrincipal
from app.core.errors import UserFacingError
from app.modules.attendance.models import AttendanceRecord, AttendanceRecordRevision, AttendanceSession
from app.modules.attendance.schemas import (
    AttendanceSummary,
    RecordOut,
    RecordWrite,
    RevisionList,
    RevisionOut,
    SessionList,
    SessionOut,
    SessionWrite,
)
from app.core.authz import ATTENDANCE_AGGREGATE_PERMISSION, Principal
from app.modules.attendance.service import cohort_totals, create_session, is_held, save_record, summarize
from app.modules.catalog.models import Cohort
from app.modules.identity.models import User
from app.modules.learning.access import cohort_scope, load_cohort, require_cohort, require_enrollment
from app.modules.learning.models import Enrollment

router = APIRouter(tags=["attendance"])

CohortId = Path(max_length=20)
_ERRORS = {403: {"description": "Sin permiso sobre la cohorte"}, 404: {"description": "No encontrado"}}


def _record_out(r: AttendanceRecord) -> RecordOut:
    return RecordOut(
        id=r.id, session_id=r.session_id, enrollment_id=r.enrollment_id, status=r.status, modality=r.modality,
        justification=r.justification, version=r.version, updated_at=r.updated_at,
    )


def _session_out(s: AttendanceSession, records: list[AttendanceRecord], timezone: str) -> SessionOut:
    return SessionOut(
        id=s.id, cohort_id=s.cohort_id, session_date=s.session_date, shift=s.shift, duration_fraction=float(s.duration_fraction),
        held=is_held(s, timezone), records=[_record_out(r) for r in records],
    )


def _sessions_in(db: DB, cohort_id: str, date_from: date | None, date_to: date | None) -> list[AttendanceSession]:
    query = select(AttendanceSession).where(AttendanceSession.cohort_id == cohort_id)
    if date_from:
        query = query.where(AttendanceSession.session_date >= date_from)
    if date_to:
        query = query.where(AttendanceSession.session_date <= date_to)
    return list(db.scalars(query.order_by(AttendanceSession.session_date, AttendanceSession.shift)))


def _records_of(db: DB, sessions: list[AttendanceSession]) -> list[AttendanceRecord]:
    ids = [s.id for s in sessions]
    return list(db.scalars(select(AttendanceRecord).where(AttendanceRecord.session_id.in_(ids)))) if ids else []


def _load_session(db: DB, session_id: uuid.UUID) -> AttendanceSession:
    session = db.get(AttendanceSession, session_id)
    if not session:
        raise UserFacingError(status.HTTP_404_NOT_FOUND, "session_not_found", "No encontramos esta sesión. Vuelve al calendario de asistencia.")
    return session


@router.post("/cohorts/{cohort_id}/attendance-sessions", response_model=SessionOut, status_code=201,
             responses={**_ERRORS, 409: {"description": "Sesión duplicada, solapada o fuera de fechas"}},
             summary="Crear una sesión de asistencia (mañana, tarde o día completo)")
def post_session(body: SessionWrite, p: CurrentPrincipal, db: DB, cohort_id: str = CohortId) -> SessionOut:
    cohort = require_cohort(db, p, "attendance.record", cohort_id)
    return _session_out(create_session(db, p, cohort, body), [], cohort.timezone)


@router.get("/cohorts/{cohort_id}/attendance-sessions", response_model=SessionList, responses=_ERRORS,
            summary="Sesiones de asistencia de una cohorte con sus registros")
def list_sessions(p: CurrentPrincipal, db: DB, cohort_id: str = CohortId, date_from: date | None = None, date_to: date | None = None) -> SessionList:
    cohort = require_cohort(db, p, "attendance.read", cohort_id)
    sessions = _sessions_in(db, cohort_id, date_from, date_to)
    records = _records_of(db, sessions)
    by_session: dict[uuid.UUID, list[AttendanceRecord]] = {s.id: [] for s in sessions}
    for r in records:
        by_session[r.session_id].append(r)
    return SessionList(cohort_id=cohort_id, items=[_session_out(s, by_session[s.id], cohort.timezone) for s in sessions])


@router.put("/attendance-sessions/{session_id}/records/{enrollment_id}", response_model=RecordOut,
            responses={**_ERRORS, 409: {"description": "Sesión futura o matrícula de otra cohorte"}, 422: {"description": "Datos incoherentes o falta el motivo de la corrección"}},
            summary="Registrar o corregir la asistencia de una persona en una sesión")
def put_record(session_id: uuid.UUID, enrollment_id: uuid.UUID, body: RecordWrite, p: CurrentPrincipal, db: DB) -> RecordOut:
    session = _load_session(db, session_id)
    cohort = require_cohort(db, p, "attendance.record", session.cohort_id)
    enrollment = db.get(Enrollment, enrollment_id)
    if not enrollment:
        raise UserFacingError(status.HTTP_404_NOT_FOUND, "enrollment_not_found", "No encontramos esta matrícula en la cohorte.")
    return _record_out(save_record(db, p, cohort, session, enrollment, body))


@router.get("/attendance-records/{record_id}/revisions", response_model=RevisionList, responses=_ERRORS,
            summary="Historial de un registro de asistencia: valor inicial y cada corrección con autor, fecha y motivo")
def list_revisions(record_id: uuid.UUID, p: CurrentPrincipal, db: DB) -> RevisionList:
    record = db.get(AttendanceRecord, record_id)
    if not record:
        raise UserFacingError(status.HTTP_404_NOT_FOUND, "record_not_found", "No encontramos este registro de asistencia.")
    require_cohort(db, p, "attendance.read", _load_session(db, record.session_id).cohort_id)
    revisions = list(db.scalars(select(AttendanceRecordRevision).where(AttendanceRecordRevision.record_id == record.id).order_by(AttendanceRecordRevision.version)))
    names = {u.id: u.display_name for u in db.scalars(select(User).where(User.id.in_({r.changed_by for r in revisions})))}
    items = [
        RevisionOut(version=r.version, status=r.status, modality=r.modality, justification=r.justification, reason=r.reason,
                    changed_by=names.get(r.changed_by), changed_at=r.changed_at)
        for r in revisions
    ]
    return RevisionList(record_id=record.id, items=items)


def _summary_access(db: DB, p: Principal, cohort_id: str, enrollment_id: uuid.UUID | None) -> tuple[Cohort, bool]:
    """Returns the cohort and whether per-enrollment rows may be shown. Coordination only gets cohort totals."""
    if enrollment_id:
        enrollment, cohort = require_enrollment(db, p, "attendance.read", enrollment_id)
        if enrollment.cohort_id != cohort_id:
            raise UserFacingError(status.HTTP_404_NOT_FOUND, "enrollment_not_found", "Esta matrícula no pertenece a la cohorte.")
        return cohort, True
    cohort = load_cohort(db, cohort_id)
    if p.can("attendance.read", cohort_scope(cohort)):
        return cohort, True
    p.require(ATTENDANCE_AGGREGATE_PERMISSION, cohort_scope(cohort))
    return cohort, False


@router.get("/cohorts/{cohort_id}/attendance-summary", response_model=AttendanceSummary, responses=_ERRORS,
            summary="Totales de asistencia por matrícula y de la cohorte (contrato get_attendance_summary del asistente)")
def get_attendance_summary(p: CurrentPrincipal, db: DB, cohort_id: str = CohortId, enrollment_id: uuid.UUID | None = Query(default=None),
                           date_from: date | None = None, date_to: date | None = None) -> AttendanceSummary:
    cohort, per_enrollment = _summary_access(db, p, cohort_id, enrollment_id)
    if enrollment_id:
        enrollment_ids = [enrollment_id]
    else:
        enrollment_ids = list(db.scalars(select(Enrollment.id).where(Enrollment.cohort_id == cohort_id, Enrollment.estado != "baja_voluntaria")
                                       .order_by(Enrollment.created_at, Enrollment.id)))
    sessions = _sessions_in(db, cohort_id, date_from, date_to)
    items = summarize(sessions, _records_of(db, sessions), enrollment_ids, cohort.timezone)
    audit.record(db, p, "attendance.summary_viewed", "cohort", cohort_id, enrollments=len(enrollment_ids), per_enrollment=per_enrollment)
    db.commit()
    return AttendanceSummary(
        cohort_id=cohort_id, timezone=cohort.timezone, date_from=date_from, date_to=date_to,
        items=items if per_enrollment else [], cohort_totals=cohort_totals(items),
    )
