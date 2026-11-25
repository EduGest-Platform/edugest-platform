import uuid
from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.modules.learning import overview_service as service


@pytest.mark.parametrize('size,recorded,suppressed,has_data', [(5, True, False, True), (5, False, False, False), (4, True, True, None)])
def test_attendance_overview_preserves_missingness_and_group_suppression(monkeypatch, size, recorded, suppressed, has_data):
    ids = [uuid.uuid4() for _ in range(size)]
    session = SimpleNamespace(id=uuid.uuid4(), session_date=date(2020, 1, 1), duration_fraction=Decimal('0.5'))
    records = [SimpleNamespace(session_id=session.id, enrollment_id=identity, status='presente', modality='presencial') for identity in ids] if recorded else []
    monkeypatch.setattr(service, 'sessions_in', lambda *args: [session])
    monkeypatch.setattr(service, 'records_of', lambda *args: records)
    monkeypatch.setattr(service, 'enrollment_ids_of', lambda *args: ids)
    cohort = SimpleNamespace(id='COH-SYN', timezone='Europe/Madrid')
    result = service.attendance_section(object(), cohort, None, None)
    assert result.totals.suppressed is suppressed and result.has_data is has_data
    assert 'enrollment_id' not in result.model_dump_json()
    if suppressed:
        assert result.totals.enrollments is None and result.totals.attendance_rate is None
    elif not recorded:
        assert result.totals.unrecorded_days == 2.5 and result.totals.attendance_rate is None
    else:
        assert result.totals.attended_days == 2.5 and result.totals.attendance_rate == 1
