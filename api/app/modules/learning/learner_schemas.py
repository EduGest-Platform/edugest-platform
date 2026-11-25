import uuid
from datetime import date
from typing import Literal

from pydantic import BaseModel

from app.modules.attendance.schemas import SUMMARY_RULE, EnrollmentAttendance
from app.modules.competencies.schemas import CurrentLevel


class LearnerEnrollment(BaseModel):
    enrollment_id: uuid.UUID
    cohort_id: str
    cohort_name: str
    status: Literal["activa", "finalizada", "baja_voluntaria"]


class LearnerEnrollments(BaseModel):
    items: list[LearnerEnrollment]


class LearnerAttendance(BaseModel):
    cohort_id: str
    timezone: str
    date_from: date | None
    date_to: date | None
    rule: str = SUMMARY_RULE
    totals: EnrollmentAttendance


class LearnerCompetencies(BaseModel):
    enrollment_id: uuid.UUID
    framework_version: int | None
    current: list[CurrentLevel]
