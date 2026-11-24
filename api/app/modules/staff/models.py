"""Invitation/access-request persistence only; no account activation or privilege grants."""
import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, utcnow


class StaffProfile(Base):
    __tablename__ = 'staff_profile'
    __table_args__ = (CheckConstraint("state IN ('pending', 'active', 'inactive')", name='ck_staff_profile_state'),)
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('app_user.id'), unique=True)
    job_title: Mapped[str | None] = mapped_column(String(120))
    state: Mapped[str] = mapped_column(String(12), default='pending', server_default='pending')
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey('app_user.id'))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Invitation(Base):
    __tablename__ = 'staff_invitation'
    __table_args__ = (
        CheckConstraint("token_hash ~ '^[0-9a-f]{64}$'", name='ck_staff_invitation_hash'),
        CheckConstraint('expires_at > created_at', name='ck_staff_invitation_expiry'),
        CheckConstraint('used_at IS NULL OR (used_at >= created_at AND used_at <= expires_at)', name='ck_staff_invitation_used'),
        CheckConstraint('revoked_at IS NULL OR revoked_at >= created_at', name='ck_staff_invitation_revoked'),
        CheckConstraint('used_at IS NULL OR revoked_at IS NULL', name='ck_staff_invitation_terminal'),
    )
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    staff_profile_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('staff_profile.id'), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey('app_user.id'))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AccessChangeRequest(Base):
    __tablename__ = 'access_change_request'
    __table_args__ = (
        CheckConstraint("requested_role IN ('admin', 'captacion', 'seleccion', 'docente', 'coordinacion')", name='ck_access_request_role'),
        CheckConstraint("scope_type IN ('global', 'program', 'call', 'cohort')", name='ck_access_request_scope'),
        CheckConstraint("(scope_type = 'global') = (scope_id IS NULL)", name='ck_access_request_scope_id'),
        CheckConstraint("state IN ('requested', 'approved', 'rejected', 'applied', 'revoked')", name='ck_access_request_state'),
        CheckConstraint('reviewed_by IS NULL OR reviewed_by <> requested_by', name='ck_access_request_distinct_reviewer'),
        CheckConstraint(
            "(state = 'requested' AND reviewed_by IS NULL AND reviewed_at IS NULL AND applied_assignment_id IS NULL) OR "
            "(state IN ('approved', 'rejected') AND reviewed_by IS NOT NULL AND reviewed_at IS NOT NULL AND applied_assignment_id IS NULL) OR "
            "(state IN ('applied', 'revoked') AND reviewed_by IS NOT NULL AND reviewed_at IS NOT NULL AND applied_assignment_id IS NOT NULL)",
            name='ck_access_request_review_shape'),
    )
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    staff_profile_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('staff_profile.id'), index=True)
    requested_role: Mapped[str] = mapped_column(String(20))
    scope_type: Mapped[str] = mapped_column(String(12))
    scope_id: Mapped[str | None] = mapped_column(String(30))
    state: Mapped[str] = mapped_column(String(12), default='requested', server_default='requested')
    requested_by: Mapped[uuid.UUID] = mapped_column(ForeignKey('app_user.id'))
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey('app_user.id'))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    applied_assignment_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey('role_assignment.id'))
