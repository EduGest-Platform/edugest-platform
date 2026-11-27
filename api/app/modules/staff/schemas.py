import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, SecretStr, model_validator


class StrictInput(BaseModel):
    model_config = ConfigDict(extra='forbid')


class InvitationCreate(StrictInput):
    user_id: uuid.UUID
    expires_hours: int = Field(default=24, ge=1, le=168)


class InvitationRenew(StrictInput):
    expires_hours: int = Field(default=24, ge=1, le=168)


class InvitationOut(BaseModel):
    id: uuid.UUID
    staff_profile_id: uuid.UUID
    created_at: datetime
    expires_at: datetime
    used_at: datetime | None
    revoked_at: datetime | None


class InvitationIssued(BaseModel):
    invitation: InvitationOut
    token: str = Field(repr=False, description='Secreto mostrado solo al emitir. No guardar en logs, tickets ni almacenamiento del navegador.')


class InvitationAccept(StrictInput):
    token: SecretStr = Field(min_length=32, max_length=128)


class StaffProfileOut(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    state: str
    job_title: str | None
    created_at: datetime


class AccessRequestCreate(StrictInput):
    requested_role: Literal['admin', 'captacion', 'seleccion', 'docente', 'coordinacion']
    scope_type: Literal['global', 'program', 'call', 'cohort']
    scope_id: str | None = Field(default=None, min_length=1, max_length=30)

    @model_validator(mode='after')
    def exact_scope(self):
        if (self.scope_type == 'global') != (self.scope_id is None):
            raise ValueError('El ámbito global no lleva ID; los demás requieren un ID.')
        return self


class AccessReview(StrictInput):
    approved: bool


class AccessRequestOut(BaseModel):
    id: uuid.UUID
    staff_profile_id: uuid.UUID
    requested_role: str
    scope_type: str
    scope_id: str | None
    state: str
    requested_by: uuid.UUID
    requested_by_name: str | None = None
    requested_at: datetime
    reviewed_by: uuid.UUID | None
    reviewed_at: datetime | None
    applied_assignment_id: uuid.UUID | None


class AccessRequestList(BaseModel):
    items: list[AccessRequestOut]
    total: int


class InvitationAccount(BaseModel):
    user_id: uuid.UUID
    display_name: str
    profile_state: Literal['pending', 'active'] | None
    latest_invitation: InvitationOut | None


class InvitationDirectory(BaseModel):
    items: list[InvitationAccount]
    has_more: bool
