from app.core import audit
from app.core.db import utcnow
from app.modules.assistant_tools.service import competency_progress, enrollment_ids_of, pending_submissions
from app.modules.attendance.queries import records_of, sessions_in
from app.modules.attendance.service import cohort_totals, summarize
from app.modules.learning.access import load_cohort
from app.modules.learning.overview_policy import require_overview_access, visible_has_data
from app.modules.learning.overview_schemas import CohortProgressOverview, OverviewAttendance, OverviewCompetencies, OverviewSubmissions


def attendance_section(db, cohort, date_from, date_to):
    sessions = sessions_in(db, cohort.id, date_from, date_to)
    enrollments = enrollment_ids_of(db, cohort.id)
    items = summarize(sessions, records_of(db, sessions), enrollments, cohort.timezone)
    totals = cohort_totals(items)
    recorded = any(item.held_days > item.unrecorded_days for item in items)
    return OverviewAttendance(date_from=date_from, date_to=date_to,
                              has_data=visible_has_data(totals.suppressed, recorded), totals=totals)


def submissions_section(db, cohort, now):
    data, has_data = pending_submissions(db, cohort, per_person=False, now=now)
    assignments = [item.model_copy(update={'counts': None}) if data.suppressed else item for item in data.assignments]
    return OverviewSubmissions(as_of=now, suppressed=data.suppressed, min_group_size=data.min_group_size,
                               has_data=visible_has_data(data.suppressed, has_data), assignments=assignments)


def competencies_section(db, cohort):
    data, has_data = competency_progress(db, cohort.id, per_person=False)
    distribution = [item.model_copy(update={'counts': None}) if data.suppressed else item for item in data.distribution]
    return OverviewCompetencies(framework_version=data.framework_version, suppressed=data.suppressed,
                                min_group_size=data.min_group_size, has_data=visible_has_data(data.suppressed, has_data),
                                distribution=distribution)


def progress_overview(db, actor, cohort_id, date_from, date_to):
    cohort = load_cohort(db, cohort_id)
    require_overview_access(actor, cohort)
    now = utcnow()
    result = CohortProgressOverview(cohort_id=cohort.id, timezone=cohort.timezone, generated_at=now,
                                    attendance=attendance_section(db, cohort, date_from, date_to),
                                    submissions=submissions_section(db, cohort, now),
                                    competencies=competencies_section(db, cohort))
    audit.record(db, actor, 'learning.progress_overview_viewed', 'cohort', cohort.id, aggregate_only=True)
    db.commit()
    return result
