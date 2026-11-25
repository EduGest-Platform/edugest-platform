from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.modules.attendance.schemas import SUMMARY_RULE, CohortAttendance


class OverviewAttendance(BaseModel):
    date_from: date | None
    date_to: date | None
    rule: str = SUMMARY_RULE
    has_data: bool | None = Field(description='Null when suppressed; false means no recorded attendance, never a zero attendance rate.')
    totals: CohortAttendance


class CohortProgressOverview(BaseModel):
    cohort_id: str
    timezone: str
    generated_at: datetime = Field(description='Response assembly time, not a historical or transaction snapshot.')
    aggregate_only: Literal[True] = True
    attendance: OverviewAttendance
