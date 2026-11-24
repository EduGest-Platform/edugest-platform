import uuid

from pydantic import SecretStr
from sqlalchemy import select

from app.core.security import token_hash
from app.modules.identity.models import User
from app.modules.staff.models import Invitation
from tests.conftest import ADMIN, CAPT_IA, CODER, SEL_IA, login


def issue(client, db, headers, account=SEL_IA):
    user_id = db.scalar(select(User.id).where(User.email == account))
    response = client.post('/api/v1/staff/invitations', headers=headers, json={'user_id': str(user_id)})
    return response


def test_rotation_revokes_old_invitation_and_receipt_is_not_cacheable(client, db):
    admin = login(client, ADMIN)
    response = issue(client, db, admin)
    assert response.status_code == 201
    assert response.headers['cache-control'] == 'no-store'
    data = response.json()
    secret = SecretStr(data.pop('token'))
    row = db.get(Invitation, uuid.UUID(data['invitation']['id']))
    if row.token_hash != token_hash(secret.get_secret_value()):
        raise AssertionError('Issued secret digest mismatch')
    renewed = client.post('/api/v1/staff/invitations/' + data['invitation']['id'] + '/renew', headers=admin, json={})
    assert renewed.status_code == 201
    db.refresh(row)
    assert row.revoked_at is not None


def test_capture_staff_cannot_invite_and_person_accounts_are_not_targets(client, db):
    assert issue(client, db, login(client, CAPT_IA)).status_code == 403
    assert issue(client, db, login(client, ADMIN), CODER).status_code == 409
