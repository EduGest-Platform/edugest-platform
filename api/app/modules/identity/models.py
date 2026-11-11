import uuid
from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base, utcnow

ROLES = ("admin", "captacion", "seleccion", "docente", "coordinacion")
SCOPE_TYPES = ("global", "program", "call", "cohort")


class Person(Base):
    """A single record per human being. Aspirant and coder are states of a Person, not roles."""

    __tablename__ = "person"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    display_name: Mapped[str] = mapped_column(String(120))
    # Normalised (trim + lower). Unique: de-duplicates expedientes.
    email: Mapped[str] = mapped_column(String(254), unique=True, index=True)
    # Reference to the synthetic prototype dataset (A-001, E-001…).
    legacy_ref: Mapped[str | None] = mapped_column(String(20), unique=True)
    is_synthetic: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class User(Base):
    __tablename__ = "app_user"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(254), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(120))
    password_hash: Mapped[str] = mapped_column(String(200))
    person_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("person.id"), unique=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    assignments: Mapped[list["RoleAssignment"]] = relationship(back_populates="user", foreign_keys="RoleAssignment.user_id")


class RoleAssignment(Base):
    """Internal permission = role + scope (global / program / call / cohort). Accumulable and revocable."""

    __tablename__ = "role_assignment"
    __table_args__ = (
        UniqueConstraint("user_id", "role", "scope_type", "scope_id", name="uq_role_assignment"),
        CheckConstraint(f"role IN {ROLES}", name="ck_role_assignment_role"),
        CheckConstraint(f"scope_type IN {SCOPE_TYPES}", name="ck_role_assignment_scope_type"),
        CheckConstraint("(scope_type = 'global') = (scope_id IS NULL)", name="ck_role_assignment_scope_id"),
    )
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("app_user.id", ondelete="CASCADE"), index=True)
    role: Mapped[str] = mapped_column(String(30))
    scope_type: Mapped[str] = mapped_column(String(10))
    scope_id: Mapped[str | None] = mapped_column(String(40))
    granted_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("app_user.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user: Mapped[User] = relationship(back_populates="assignments", foreign_keys=[user_id])


class AuthSession(Base):
    __tablename__ = "auth_session"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("app_user.id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
