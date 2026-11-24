"""KAN-157: discover only cohorts already allowed by academic scope."""

from sqlalchemy import select

from app.core.db import utcnow
from app.modules.identity.models import RoleAssignment, User
from tests.conftest import ADMIN, CAPT_IA, CODER, COORD, DOCENTE, login


def test_directory_requires_authentication(client):
    assert client.get('/api/v1/cohorts').status_code == 401


def test_teacher_directory_excludes_other_program_and_has_no_roster(client, db):
    # The shared demo teacher is assigned to BOTH seeded cohorts. Restrict this
    # negative-scope scenario explicitly instead of assuming a single assignment.
    user_id = db.scalar(select(User.id).where(User.email == DOCENTE))
    assignments = db.scalars(select(RoleAssignment).where(RoleAssignment.user_id == user_id))
    for assignment in assignments:
        if (assignment.role, assignment.scope_type, assignment.scope_id) != ('docente', 'cohort', 'COH-IA'):
            assignment.revoked_at = utcnow()
    db.commit()
    response = client.get('/api/v1/cohorts', headers=login(client, DOCENTE))
    assert response.status_code == 200
    rows = response.json()
    assert rows and {c['id'] for c in rows} == {'COH-IA'}
    assert all(c['can_record_attendance'] for c in rows)
    assert set(rows[0]) == {'id', 'program_id', 'nombre', 'inicio', 'fin', 'timezone', 'can_record_attendance'}


def test_teacher_directory_retains_all_authorized_cohorts(client):
    response = client.get('/api/v1/cohorts', headers=login(client, DOCENTE))
    assert response.status_code == 200
    rows = response.json()
    assert {c['id'] for c in rows} == {'COH-IA', 'COH-DATA'}
    assert all(c['can_record_attendance'] for c in rows)


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
