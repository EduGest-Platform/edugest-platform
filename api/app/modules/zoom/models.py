"""Persistence for Zoom meetings and reviewable notes."""
import uuid
from datetime import datetime

from sqlalchemy import JSON, CheckConstraint, DateTime, ForeignKey, Integer, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, utcnow


class ZoomMeeting(Base):
    __tablename__ = "zoom_meeting"
    __table_args__ = (
        CheckConstraint("authentication_mode IN ('open', 'authenticated', 'institutional')", name="ck_zoom_auth_mode"),
        CheckConstraint("(authentication_mode = 'institutional' AND profile_id IS NOT NULL) OR (authentication_mode <> 'institutional' AND profile_id IS NULL)", name="ck_zoom_auth_profile"),
        CheckConstraint("duration_minutes BETWEEN 1 AND 1440", name="ck_zoom_duration"),
    )
    session_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("attendance_session.id"), primary_key=True)
    provider_id: Mapped[str] = mapped_column(String(32), unique=True)
    join_url: Mapped[str] = mapped_column(String(2048))
    host_id: Mapped[str] = mapped_column(String(255))
    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    duration_minutes: Mapped[int] = mapped_column(Integer)
    authentication_mode: Mapped[str] = mapped_column(String(20))
    profile_id: Mapped[str | None] = mapped_column(String(255))
    ai_settings: Mapped[dict] = mapped_column(JSON)
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("app_user.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ZoomProvisioningIntent(Base):
    __tablename__ = "zoom_provisioning_intent"
    __table_args__ = (
        CheckConstraint("state IN ('pending', 'uncertain', 'confirmed')", name="ck_zoom_intent_state"),
    )

    session_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("attendance_session.id"), primary_key=True)
    operation_id: Mapped[uuid.UUID] = mapped_column(Uuid, unique=True)
    state: Mapped[str] = mapped_column(String(16))
    host_id: Mapped[str] = mapped_column(String(255))
    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    duration_minutes: Mapped[int] = mapped_column(Integer)
    authentication_mode: Mapped[str] = mapped_column(String(20))
    profile_id: Mapped[str | None] = mapped_column(String(255))
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("app_user.id"))
    updated_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("app_user.id"))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ZoomNotesVersion(Base):
    __tablename__ = "zoom_notes_version"
    __table_args__ = (
        UniqueConstraint("session_id", "version", name="uq_zoom_notes_version"),
        CheckConstraint("version >= 1", name="ck_zoom_notes_version"),
        CheckConstraint("(approved_by IS NULL AND approved_at IS NULL) OR (approved_by IS NOT NULL AND approved_at IS NOT NULL)", name="ck_zoom_notes_approval"),
    )
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("zoom_meeting.session_id"), index=True)
    version: Mapped[int] = mapped_column(Integer)
    body: Mapped[dict] = mapped_column(JSON)
    transcript_sha256: Mapped[str] = mapped_column(String(64))
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("app_user.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    approved_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("app_user.id"))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
