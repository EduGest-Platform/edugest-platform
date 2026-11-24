"""KAN-157: discover only cohorts already allowed by academic scope."""

from tests.conftest import ADMIN, CAPT_IA, CODER, COORD, DOCENTE, login


def test_directory_requires_authentication(client):
    assert client.get('/api/v1/cohorts').status_code == 401


def test_teacher_directory_excludes_other_program_and_has_no_roster(client):
    response = client.get('/api/v1/cohorts', headers=login(client, DOCENTE))
    assert response.status_code == 200
    rows = response.json()
    assert rows and {c['id'] for c in rows} == {'COH-IA'}
    assert all(c['can_record_attendance'] for c in rows)
    assert set(rows[0]) == {'id', 'program_id', 'nombre', 'inicio', 'fin', 'timezone', 'can_record_attendance'}


def test_coordination_directory_does_not_offer_recording(client):
    rows = client.get('/api/v1/cohorts', headers=login(client, COORD)).json()
    assert rows and all(not c['can_record_attendance'] for c in rows)


def test_unprivileged_roles_do_not_discover_cohorts(client):
    for user in (CODER, CAPT_IA):
        response = client.get('/api/v1/cohorts', headers=login(client, user))
        assert response.status_code == 200 and response.json() == []


def test_admin_can_discover_multiple_cohorts(client):
    rows = client.get('/api/v1/cohorts', headers=login(client, ADMIN)).json()
    assert {'COH-IA', 'COH-DATA'} <= {c['id'] for c in rows}
