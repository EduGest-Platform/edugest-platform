import uuid
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from app.modules.assistant_tools.schemas import AssignmentStatus, EnrollmentPending, PendingSubmissions, StateCount
from app.modules.learning import overview_service as service


@pytest.mark.parametrize('suppressed,has_data', [(False, True), (False, False), (True, True), (True, False)])
def test_submission_section_uses_aggregate_query_and_discards_individual_rows(monkeypatch, suppressed, has_data):
    now = datetime(2030, 1, 1, tzinfo=timezone.utc)
    individual = uuid.uuid4()
    activity = AssignmentStatus(assignment_id=uuid.uuid4(), title='Synthetic activity', due_at=now,
        counts=StateCount(on_time=5, late=0, pending=1, overdue=0, reviewed=2))
    source = PendingSubmissions(timezone='Europe/Madrid', suppressed=suppressed, min_group_size=5,
        assignments=[activity], items=[EnrollmentPending(enrollment_id=individual, states={})])
    calls = []

    def query(db, cohort, per_person, now):
        calls.append((per_person, now))
        return source, has_data

    monkeypatch.setattr(service, 'pending_submissions', query)
    result = service.submissions_section(object(), SimpleNamespace(id='COH-SYN'), now)
    assert calls == [(False, now)]
    assert result.as_of == now and result.period == 'current_published_assignments'
    assert result.has_data is (None if suppressed else has_data)
    assert 'enrollment_id' not in result.model_dump_json() and str(individual) not in result.model_dump_json()
    assert result.assignments[0].counts == (None if suppressed else activity.counts)
