from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.modules.attendance.schemas import SUMMARY_RULE, CohortAttendance
from app.modules.assistant_tools.schemas import AssignmentStatus
from app.modules.submissions.schemas import DELIVERY_RULE


class OverviewAttendance(BaseModel):
    date_from: date | None
    date_to: date | None
    rule: str = SUMMARY_RULE
    has_data: bool | None = Field(description='Null when suppressed; false means no recorded attendance, never a zero attendance rate.')
    totals: CohortAttendance


class OverviewSubmissions(BaseModel):
    as_of: datetime
    period: Literal['current_published_assignments'] = 'current_published_assignments'
    rule: str = DELIVERY_RULE
    has_data: bool | None
    suppressed: bool
    min_group_size: int
    assignments: list[AssignmentStatus]


class CohortProgressOverview(BaseModel):
    cohort_id: str
    timezone: str
    generated_at: datetime = Field(description='Response assembly time, not a historical or transaction snapshot.')
    aggregate_only: Literal[True] = True
    attendance: OverviewAttendance
    submissions: OverviewSubmissions
