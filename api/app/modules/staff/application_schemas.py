import uuid

from pydantic import BaseModel, Field, field_validator

from app.modules.staff.schemas import AccessRequestCreate


class AccessApply(AccessRequestCreate):
    confirm: bool = Field(strict=True, description='Explicit administrative confirmation of the echoed role and scope.')

    @field_validator('confirm')
    @classmethod
    def confirmation_required(cls, value):
        if not value:
            raise ValueError('Se requiere confirmación administrativa explícita.')
        return value


class AccessApplicationPreview(BaseModel):
    request_id: uuid.UUID
    user_id: uuid.UUID
    requested: AccessRequestCreate
    can_apply: bool
    blockers: list[str]


class AccessApplicationOut(BaseModel):
    request_id: uuid.UUID
    request_state: str
    assignment_id: uuid.UUID | None
    assignment_active: bool | None = Field(description='Whether the linked role row is unrevoked; not a claim of effective permissions or account activation.')
