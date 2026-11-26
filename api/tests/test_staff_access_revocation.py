import uuid

from sqlalchemy import select

from app.modules.audit.models import AuditEvent
from app.modules.identity.models import RoleAssignment
from tests.conftest import ADMIN, SEL_IA, login
from tests.test_selection_decisions import make_cohort
from tests.test_staff_access_review import active_profile

ROOT = '/api/v1/staff/access-requests'


def grant(client, owner, admin, cohort='COH-IA'):
    requested = {'requested_role': 'docente', 'scope_type': 'cohort', 'scope_id': cohort}
    request = client.post(ROOT, headers=owner, json=requested)
    assert request.status_code == 201
    target = f"{ROOT}/{request.json()['id']}"
    assert client.post(f'{target}/review', headers=admin, json={'approved': True}).status_code == 200
    applied = client.post(f'{target}/apply', headers=admin, json={**requested, 'confirm': True})
    assert applied.status_code == 200
    return target, {**requested, 'confirm': True, 'assignment_id': applied.json()['assignment_id']}


def test_revoking_scoped_assignment_is_idempotent_and_preserves_regrant_history(client, db):
    owner = active_profile(client, db, SEL_IA)
    admin = login(client, ADMIN)
    target, confirmation = grant(client, owner, admin)
    endpoint = f'{target}/revoke-access'
    team = '/api/v1/cohorts/COH-IA/teaching-team'
    assert client.get(team, headers=owner).status_code == 200
    assert client.post(endpoint, headers=owner, json=confirmation).status_code == 403
    assert client.post(endpoint, headers=admin, json={**confirmation, 'assignment_id': str(uuid.uuid4())}).status_code == 409
    assert client.post(endpoint, headers=admin, json={**confirmation, 'scope_id': 'COH-DATA'}).status_code == 409
    revoked = client.post(endpoint, headers=admin, json=confirmation)
    assert revoked.status_code == 200
    assert revoked.json()['request_state'] == 'revoked' and revoked.json()['assignment_active'] is False
    assert client.post(endpoint, headers=admin, json=confirmation).json() == revoked.json()
    assert client.get(team, headers=owner).status_code == 403
    assert client.get(f'{target}/application', headers=owner).json() == revoked.json()

    new_target, new_confirmation = grant(client, owner, admin)
    assert new_confirmation['assignment_id'] != confirmation['assignment_id']
    assert client.get(team, headers=owner).status_code == 200
    assert client.get(f'{target}/application', headers=owner).json() == revoked.json()
    assert client.get(f'{new_target}/application', headers=owner).json()['assignment_active'] is True
    assert len(list(db.scalars(select(AuditEvent).where(AuditEvent.action == 'staff.access_revoked')))) == 1
    previous = db.get(RoleAssignment, uuid.UUID(confirmation['assignment_id']))
    assert previous.revoked_at is not None


def test_last_cohort_teacher_can_only_be_revoked_after_another_teacher_exists(client, db):
    cohort = make_cohort(db)
    owner = active_profile(client, db, SEL_IA)
    admin = login(client, ADMIN)
    target, confirmation = grant(client, owner, admin, cohort.id)
    response = client.post(f'{target}/revoke-access', headers=admin, json=confirmation)
    assert response.status_code == 409 and response.json()['code'] == 'last_teacher'
    assert client.get(f'{target}/application', headers=owner).json()['assignment_active'] is True


def test_teaching_roster_revocation_preserves_staff_grant_history_when_readded(client, db):
    owner = active_profile(client, db, SEL_IA)
    admin = login(client, ADMIN)
    target, _ = grant(client, owner, admin)
    user_id = client.get('/api/v1/auth/me', headers=owner).json()['id']
    team = f'/api/v1/cohorts/COH-IA/teaching-team/{user_id}'
    assert client.delete(team, headers=admin).status_code == 200
    assert client.put(team, headers=admin).status_code == 200
    status = client.get(f'{target}/application', headers=owner).json()
    assert status['request_state'] == 'revoked' and status['assignment_active'] is False


def test_old_revocation_cannot_remove_a_new_grant(client, db):
    owner = active_profile(client, db, SEL_IA)
    admin = login(client, ADMIN)
    old_target, old_confirmation = grant(client, owner, admin)
    old_endpoint = f'{old_target}/revoke-access'
    assert client.post(old_endpoint, headers=admin, json=old_confirmation).status_code == 200

    new_target, new_confirmation = grant(client, owner, admin)
    assert new_confirmation['assignment_id'] != old_confirmation['assignment_id']
    assert client.post(old_endpoint, headers=admin, json=new_confirmation).status_code == 409
    assert client.post(f'{new_target}/revoke-access', headers=admin, json=old_confirmation).status_code == 409
    assert client.post(old_endpoint, headers=admin, json=old_confirmation).status_code == 200

    current = client.get(f'{new_target}/application', headers=owner).json()
    assert current['request_state'] == 'applied'
    assert current['assignment_active'] is True
    assert current['assignment_id'] == new_confirmation['assignment_id']
    assert client.get('/api/v1/cohorts/COH-IA/teaching-team', headers=owner).status_code == 200
    assert len(list(db.scalars(select(AuditEvent).where(AuditEvent.action == 'staff.access_revoked')))) == 1
