from tests.conftest import CAPT_IA, COORD, DOCENTE, login

PATH = '/api/v1/cohorts/COH-IA/progress-overview'


def test_overview_matches_existing_attendance_aggregate_for_authorized_roles(client):
    for account in (COORD, DOCENTE):
        headers = login(client, account)
        response = client.get(PATH, headers=headers)
        assert response.status_code == 200
        previous = client.get('/api/v1/cohorts/COH-IA/attendance-summary', headers=headers)
        assert response.json()['attendance']['totals'] == previous.json()['cohort_totals']
        assert response.json()['aggregate_only'] is True
        assert response.headers['cache-control'] == 'no-store'


def test_unauthorized_role_is_denied_before_reversed_period_validation(client):
    query = '?attendance_from=2030-02-01&attendance_to=2030-01-01'
    assert client.get(PATH + query, headers=login(client, CAPT_IA)).status_code == 403
    response = client.get(PATH + query, headers=login(client, COORD))
    assert response.status_code == 422 and response.json()['code'] == 'invalid_date_window'
