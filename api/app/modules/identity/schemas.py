import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class LoginIn(BaseModel):
    email: str = Field(max_length=254)
    password: str = Field(min_length=1, max_length=200)


class RoleAssignmentOut(BaseModel):
    role: str
    scope_type: str
    scope_id: str | None


class EnrollmentOut(BaseModel):
    cohort_id: str
    estado: str


class MeOut(BaseModel):
    id: uuid.UUID
    display_name: str
    email: str
    person_id: uuid.UUID | None
    roles: list[RoleAssignmentOut]
    # Lifecycle states of the linked Person (not permissions).
    application_ids: list[uuid.UUID]
    enrollments: list[EnrollmentOut]


class LoginOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_at: datetime
    me: MeOut
