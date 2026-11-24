"""KAN-187: REST and assistant aggregates share date-window validation after scope authorization."""
import pytest
from sqlalchemy import func, select

from app.modules.audit.models import AuditEvent
from tests.conftest import CAPT_IA, DOCENTE, login


@pytest.mark.parametrize('path', [
    '/api/v1/cohorts/COH-IA/attendance-sessions',
    '/api/v1/cohorts/COH-IA/attendance-summary',
    '/api/v1/assistant/tools/attendance-summary?cohort_id=COH-IA',
])
def test_inverted_period_does_not_return_empty_successful_metrics(client, db, path):
    headers = login(client, DOCENTE)
    before = db.scalar(select(func.count()).select_from(AuditEvent))
    separator = '&' if '?' in path else '?'
    response = client.get(path + separator + 'date_from=2026-11-25&date_to=2026-11-24', headers=headers)
    assert response.status_code == 422
    assert response.json()['code'] == 'invalid_date_window'
    assert db.scalar(select(func.count()).select_from(AuditEvent)) == before
    denied = client.get(path + separator + 'date_from=2026-11-25&date_to=2026-11-24', headers=login(client, CAPT_IA))
    assert denied.status_code == 403
