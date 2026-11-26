import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.core.text import normalize_email

Stage = Literal["enviada", "requisitos_en_revision", "convocada", "evaluacion_en_curso", "pendiente_decision_humana", "admitida", "lista_espera", "no_admitida", "retirada"]


def _strip_if_str(value: object) -> object:
    """Trim text before length validation without coercing other input types."""
    return value.strip() if isinstance(value, str) else value


class ApplicationCreate(BaseModel):
    """Public inscription form. Only the minimum data needed for pre-selection (data minimisation)."""

    call_id: str = Field(min_length=1, max_length=30)
    nombre: str = Field(min_length=2, max_length=120)
    email: str = Field(max_length=254)
    motivacion: str = Field(min_length=10, max_length=2000)
    disponibilidad: Literal["Mañana", "Tarde", "Flexible"]
    acepta_datos_sinteticos: Literal[True] = Field(description="Confirmación obligatoria: el entorno solo usa datos sintéticos")

    @field_validator("call_id")
    @classmethod
    def _nonblank_call(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Selecciona una convocatoria.")
        return value

    @field_validator("acepta_datos_sinteticos", mode="before")
    @classmethod
    def _explicit_synthetic_confirmation(cls, value: object) -> Literal[True]:
        if value is not True:
            raise ValueError("Confirma el uso de datos sintéticos.")
        return True

    @field_validator("email")
    @classmethod
    def _email(cls, v: str) -> str:
        return normalize_email(v)

    @field_validator("nombre", "motivacion", mode="before")
    @classmethod
    def _trim_text(cls, v: object) -> object:
        return _strip_if_str(v)


class ApplicationReceipt(BaseModel):
    id: uuid.UUID
    codigo: str
    call_id: str
    stage: Stage
    created_at: datetime


class PersonOut(BaseModel):
    id: uuid.UUID
    display_name: str
    email: str


class ApplicationSummary(BaseModel):
    id: uuid.UUID
    codigo: str
    legacy_ref: str | None
    call_id: str
    program_id: str
    stage: Stage
    person: PersonOut
    created_at: datetime
    updated_at: datetime


class ApplicationList(BaseModel):
    items: list[ApplicationSummary]
    total: int


EventType = Literal["contacto", "nota", "recordatorio"]
Channel = Literal["email", "telefono", "presencial", "videollamada"]
ContactResult = Literal["respondida", "sin_respuesta"]


class NextActionCreate(BaseModel):
    """What happens next after a contact. It is a work reminder for staff: nothing is sent to anyone."""

    description: str = Field(min_length=1, max_length=200, description="Acción operativa. No incluir datos de salud, situación personal ni otros datos sensibles.")
    owner_user_id: uuid.UUID = Field(description="Personal con permiso CRM en la convocatoria (ver crm-owners).")
    due_on: date = Field(description="Plazo; no puede ser anterior a hoy (Europe/Madrid).")

    @field_validator("description", mode="before")
    @classmethod
    def _trim_description(cls, v: object) -> object:
        return _strip_if_str(v)


class NextActionOut(BaseModel):
    description: str
    owner_user_id: uuid.UUID
    owner: str
    due_on: date


class CrmOwnerOut(BaseModel):
    user_id: uuid.UUID
    display_name: str


class EventCreate(BaseModel):
    tipo: EventType
    resultado: ContactResult | None = Field(None, description="Solo para contactos: «sin_respuesta» cuenta para la revisión de silencio.")
    canal: Channel | None = None
    resumen: str = Field(min_length=1, max_length=500, description="Resumen operativo. No incluir datos de salud, situación personal ni otros datos sensibles.")

    next_action: NextActionCreate | None = Field(None, description="Solo para contactos. Opcional; si se envía, exige los tres campos.")

    @field_validator("resumen", mode="before")
    @classmethod
    def _trim_summary(cls, v: object) -> object:
        return _strip_if_str(v)


class EventOut(BaseModel):
    id: uuid.UUID
    tipo: str
    canal: str | None
    resultado: str | None
    resumen: str
    actor: str | None
    occurred_at: datetime
    next_action: NextActionOut | None


class ApplicationDetail(ApplicationSummary):
    motivacion: str
    disponibilidad: str
    events: list[EventOut]
    next_action: NextActionOut | None = Field(description="Próxima acción vigente: la del contacto más reciente que registró una.")


class ApplicationSelfView(BaseModel):
    """What an aspirant sees about their own application: no internal notes or CRM history."""

    id: uuid.UUID
    codigo: str
    call_id: str
    call_nombre: str
    stage: Stage
    created_at: datetime
    updated_at: datetime
