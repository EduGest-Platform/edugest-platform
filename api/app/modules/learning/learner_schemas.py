import uuid
from typing import Literal

from pydantic import BaseModel


class LearnerEnrollment(BaseModel):
    enrollment_id: uuid.UUID
    cohort_id: str
    cohort_name: str
    status: Literal["activa", "finalizada", "baja_voluntaria"]


class LearnerEnrollments(BaseModel):
    items: list[LearnerEnrollment]
