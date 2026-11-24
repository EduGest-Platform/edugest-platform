import uuid

from sqlalchemy import func, select

from app.modules.identity.models import RoleAssignment
from app.modules.staff.models import Invitation, StaffProfile
from tests.conftest import ADMIN, CAPT_IA, SEL_IA, login
from tests.test_staff_issuance import issue


def test_acceptance_activates_own_profile_once_without_granting_roles(client, db):
    receipt = issue(client, db, login(client, ADMIN)).json()
    caller = login(client, SEL_IA)
    before = db.scalar(select(func.count()).select_from(RoleAssignment))
    response = client.post('/api/v1/staff/invitations/accept', headers=caller, json={'token': receipt['token']})
    assert response.status_code == 200 and response.json()['state'] == 'active'
    assert db.scalar(select(func.count()).select_from(RoleAssignment)) == before
    replay = client.post('/api/v1/staff/invitations/accept', headers=caller, json={'token': receipt['token']})
    assert replay.status_code == 400 and replay.json()['code'] == 'invitation_unavailable'
    assert client.get('/api/v1/staff/me', headers=caller).json()['id'] == response.json()['id']


def test_foreign_account_cannot_consume_a_valid_invitation(client, db):
    receipt = issue(client, db, login(client, ADMIN)).json()
    response = client.post('/api/v1/staff/invitations/accept', headers=login(client, CAPT_IA), json={'token': receipt['token']})
    assert response.status_code == 400 and response.json()['code'] == 'invitation_unavailable'
    row = db.get(Invitation, uuid.UUID(receipt['invitation']['id']))
    db.refresh(row)
    assert row.used_at is None
    assert db.get(StaffProfile, row.staff_profile_id).state == 'pending'
