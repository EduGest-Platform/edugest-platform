import pytest

from app.seed import load_seed
from app.seed_academic import load_academic
from tests.conftest import CAPT_IA, COORD, DOCENTE, login

PATH = '/api/v1/cohorts/COH-IA/progress-overview'


@pytest.fixture
def academic(db):
    load_academic(db, load_seed())


def test_overview_matches_existing_attendance_aggregate_for_authorized_roles(client, academic):
    for account in (COORD, DOCENTE):
        headers = login(client, account)
        response = client.get(PATH, headers=headers)
        assert response.status_code == 200
        previous = client.get('/api/v1/cohorts/COH-IA/attendance-summary', headers=headers)
        assert response.json()['attendance']['totals'] == previous.json()['cohort_totals']
        assert response.json()['aggregate_only'] is True
        assert response.headers['cache-control'] == 'no-store'


def test_unauthorized_role_is_denied_before_reversed_period_validation(client, academic):
    query = '?attendance_from=2030-02-01&attendance_to=2030-01-01'
    assert client.get(PATH + query, headers=login(client, CAPT_IA)).status_code == 403
    response = client.get(PATH + query, headers=login(client, COORD))
    assert response.status_code == 422 and response.json()['code'] == 'invalid_date_window'


def test_overview_submission_counts_match_the_existing_aggregate_tool(client, academic):
    headers = login(client, COORD)
    overview = client.get(PATH, headers=headers)
    previous = client.get('/api/v1/tools/pending-submissions?cohort_id=COH-IA', headers=headers)
    assert overview.status_code == previous.status_code == 200
    assert overview.json()['submissions']['assignments'] == previous.json()['data']['assignments']
    assert 'items' not in overview.json()['submissions']


def test_overview_competencies_match_the_existing_aggregate_tool(client, academic):
    headers = login(client, COORD)
    overview = client.get(PATH, headers=headers)
    previous = client.get('/api/v1/tools/competency-progress?cohort_id=COH-IA', headers=headers)
    assert overview.status_code == previous.status_code == 200
    assert overview.json()['competencies']['distribution'] == previous.json()['data']['distribution']
    assert overview.json()['competencies']['framework_version'] == previous.json()['data']['framework_version']
    assert 'items' not in overview.json()['competencies']
