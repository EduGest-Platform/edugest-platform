"""Prepared write operations, not enabled or mounted while migration is pending.

One request-owned Session per operation. Every attendance writer must acquire
the cohort lock before checking session overlaps or record versions. No DDL,
seed, enrollment changes or migration execution occurs in this module.
"""

from collections.abc import Iterator
from contextlib import contextmanager
from uuid import UUID
from zoneinfo import ZoneInfo

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core import audit
from app.core.authz import Principal
from app.core.db import utcnow
from app.modules.catalog.models import Cohort
from app.modules.learning.attendance_models import AttendanceRecord, AttendanceRevision, AttendanceSession
from app.modules.learning.attendance_policy import (
    audit_metadata, can_write, out_of_scope, require_any_attendance_write, validate_record_change, validate_session_creation,
)
from app.modules.learning.attendance_schemas import PERIOD_DURATION, AttendanceRecordWrite, AttendanceSessionCreate
from app.modules.learning.models import Enrollment


class AttendanceWriter:
    def __init__(self, db: Session, *, schema_enabled: bool = False):
        self.db = db
        self.schema_enabled = schema_enabled

    @contextmanager
    def _transaction(self) -> Iterator[None]:
        if not self.schema_enabled:
            raise HTTPException(503, "La persistencia académica está pendiente de habilitar")
        try:
            yield
            self.db.commit()
        except IntegrityError as error:
            self.db.rollback()
            raise HTTPException(409, "El registro ya existe o ha cambiado; vuelve a cargarlo") from error
        except Exception:
            self.db.rollback()
            raise

    def _lock_cohort(self, cohort_id: str) -> Cohort:
        cohort = self.db.scalar(select(Cohort).where(Cohort.id == cohort_id).with_for_update())
        if cohort is None:
            raise HTTPException(404, "Cohorte no encontrada")
        return cohort

    def _deny(self, actor: Principal, cohort_id: str, **meta) -> HTTPException:
        """Audits the out-of-scope attempt (ids only) and commits it before the explained 403 is raised."""
        audit.record(self.db, actor, "attendance.access_denied", "cohort", cohort_id, **meta)
        self.db.commit()
        return out_of_scope()

    def create_session(self, actor: Principal, cohort_id: str, body: AttendanceSessionCreate) -> AttendanceSession:
        with self._transaction():
            require_any_attendance_write(actor)
            cohort = self._lock_cohort(cohort_id)
            if not can_write(actor, cohort.program_id, cohort_id, correction=False):
                raise self._deny(actor, cohort_id, action="create_session")
            periods = list(self.db.scalars(select(AttendanceSession.period).where(
                AttendanceSession.cohort_id == cohort_id, AttendanceSession.session_date == body.session_date,
            )))
            validate_session_creation(cohort, body.session_date, body.period, periods)
            session = AttendanceSession(
                cohort_id=cohort_id, session_date=body.session_date, period=body.period,
                duration_fraction=PERIOD_DURATION[body.period], modality=body.modality,
                created_by_user_id=actor.user.id, created_at=utcnow(),
            )
            self.db.add(session)
            self.db.flush()
            audit.record(self.db, actor, "attendance.session_created", "cohort", cohort_id, session_id=str(session.id))
        return session

    def save_record(
        self, actor: Principal, session_id: UUID, enrollment_id: UUID, body: AttendanceRecordWrite,
    ) -> tuple[AttendanceRecord, bool]:
        with self._transaction():
            require_any_attendance_write(actor)
            session = self.db.scalar(select(AttendanceSession).where(AttendanceSession.id == session_id))
            if session is None:
                raise HTTPException(404, "Sesión no encontrada")
            # Every writer takes the cohort lock before checking overlaps or versions.
            cohort = self._lock_cohort(session.cohort_id)
            self.db.refresh(session)
            enrollment = self.db.scalar(select(Enrollment).where(
                Enrollment.id == enrollment_id, Enrollment.cohort_id == session.cohort_id,
            ).with_for_update())
            if enrollment is None:
                raise HTTPException(404, "Matrícula no encontrada en esta cohorte")
            record = self.db.scalar(select(AttendanceRecord).where(
                AttendanceRecord.session_id == session_id, AttendanceRecord.enrollment_id == enrollment_id,
            ).with_for_update().execution_options(populate_existing=True))
            if not can_write(actor, cohort.program_id, session.cohort_id, correction=record is not None):
                raise self._deny(actor, session.cohort_id, action="save_record", session_id=str(session.id))
            validate_record_change(
                period=session.period, session_cohort_id=session.cohort_id, enrollment_cohort_id=enrollment.cohort_id,
                enrollment_status=enrollment.estado, session_date=session.session_date,
                today=utcnow().astimezone(ZoneInfo("Europe/Madrid")).date(),
                body=body, current_version=record.version if record else None,
            )
            created = record is None
            now = utcnow()
            if record is None:
                record = AttendanceRecord(
                    cohort_id=session.cohort_id, session_id=session.id, enrollment_id=enrollment.id, version=1,
                )
                self.db.add(record)
            else:
                record.version += 1
            record.status, record.justified = body.status, body.justified
            record.recorded_by_user_id, record.recorded_at = actor.user.id, now
            self.db.flush()
            self.db.add(AttendanceRevision(
                record_id=record.id, version=record.version, status=body.status, justified=body.justified,
                actor_user_id=actor.user.id, occurred_at=now, correction_reason=None if created else body.correction_reason,
            ))
            audit.record(
                self.db, actor, "attendance.record_created" if created else "attendance.record_corrected",
                "cohort", session.cohort_id, **audit_metadata(record.id, session.id, enrollment.id, record.version, now),
            )
        return record, created
