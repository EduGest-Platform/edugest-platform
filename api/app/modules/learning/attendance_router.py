"""Prepared attendance read route; mount only with an approved persistence adapter."""

from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response

from app.core.db import utcnow
from app.core.deps import CurrentPrincipal
from app.modules.learning.attendance_schemas import ABSENCE_DAYS, AttendanceRecordOut, AttendanceRecordWrite, AttendanceSessionCreate, AttendanceSessionOut, AttendanceSummary
from app.modules.learning.attendance_service import AttendanceWriter
from app.modules.learning.attendance_summary import AttendanceReader, get_attendance_summary

router = APIRouter(tags=["attendance"])


def attendance_reader() -> AttendanceReader:
    # Never silently replace missing PostgreSQL integration with synthetic data.
    raise HTTPException(503, "La consulta académica está pendiente de habilitar")


def attendance_writer() -> AttendanceWriter:
    raise HTTPException(503, "El registro académico está pendiente de habilitar")


@router.post(
    "/cohorts/{cohort_id}/attendance-sessions", response_model=AttendanceSessionOut, status_code=201,
    responses={403: {"description": "Sin permiso o fuera de ámbito (explicado y auditado)"}, 404: {"description": "Cohorte no encontrada"},
               409: {"description": "Sesión duplicada o solapada"}, 503: {"description": "Persistencia no habilitada"}},
    summary="Preparar una sesión lectiva de la cohorte, sin convertir registros ausentes en asistencia",
)
def create_attendance_session(
    cohort_id: str, body: AttendanceSessionCreate, p: CurrentPrincipal,
    writer: Annotated[AttendanceWriter, Depends(attendance_writer)],
) -> AttendanceSessionOut:
    session = writer.create_session(p, cohort_id, body)
    return AttendanceSessionOut(
        id=session.id, cohort_id=session.cohort_id, session_date=session.session_date,
        period=session.period, duration_fraction=session.duration_fraction, modality=session.modality,
    )


@router.put(
    "/attendance-sessions/{session_id}/records/{enrollment_id}", response_model=AttendanceRecordOut,
    responses={201: {"model": AttendanceRecordOut, "description": "Primer registro creado"},
               403: {"description": "Sin permiso o fuera de ámbito (explicado y auditado)"}, 404: {"description": "Sesión o matrícula no encontrada"},
               409: {"description": "Versión desfasada, sesión futura o matrícula no activa"}, 503: {"description": "Persistencia no habilitada"}},
    summary="Registrar o corregir asistencia con versión esperada e historial",
)
def put_attendance_record(
    session_id: UUID, enrollment_id: UUID, body: AttendanceRecordWrite, response: Response, p: CurrentPrincipal,
    writer: Annotated[AttendanceWriter, Depends(attendance_writer)],
) -> AttendanceRecordOut:
    record, created = writer.save_record(p, session_id, enrollment_id, body)
    if created:
        response.status_code = 201
    return AttendanceRecordOut(
        id=record.id, session_id=record.session_id, enrollment_id=record.enrollment_id, status=record.status,
        justified=record.justified, absence_days=ABSENCE_DAYS[record.status], recorded_at=record.recorded_at, version=record.version,
    )


@router.get(
    "/enrollments/{enrollment_id}/attendance-summary",
    response_model=AttendanceSummary,
    responses={
        401: {"description": "Sesión no válida"},
        403: {"description": "Sin permiso académico o matrícula fuera de ámbito (explicado y auditado)"},
        404: {"description": "Matrícula no encontrada"},
        503: {"description": "Persistencia académica no habilitada"},
    },
    summary="Resumen de asistencia registrado, con periodo, cobertura y datos desconocidos",
    description="No interpreta un registro ausente como cero faltas. El ámbito se deriva de la matrícula y la sesión autenticada, nunca del modelo.",
)
def read_attendance_summary(
    enrollment_id: UUID, p: CurrentPrincipal,
    reader: Annotated[AttendanceReader, Depends(attendance_reader)],
    date_from: date = Query(), date_to: date = Query(),
) -> AttendanceSummary:
    return get_attendance_summary(reader, p, enrollment_id, date_from, date_to, as_of=utcnow())
