import uuid
from datetime import timedelta

from sqlalchemy import func, select

from app.core.db import utcnow
from app.modules.identity.models import RoleAssignment
from app.modules.staff.models import Invitation
from tests.conftest import ADMIN, CAPT_IA, CODER, SEL_IA, login

DIRECTORY = '/api/v1/staff/invitation-accounts'
INVITATIONS = '/api/v1/staff/invitations'


def test_directory_lists_only_admin_eligible_accounts_and_limits_results(client):
    assert client.get(DIRECTORY).status_code == 401
    for email in (CAPT_IA, CODER):
        assert client.get(DIRECTORY, headers=login(client, email)).status_code == 403
    admin = login(client, ADMIN)
    response = client.get(DIRECTORY, headers=admin, params={'limit': 1})
    assert response.status_code == 200
    assert len(response.json()['items']) == 1 and response.json()['has_more']
    filtered = client.get(DIRECTORY, headers=admin, params={'search': 'Selección IA'})
    assert [row['display_name'] for row in filtered.json()['items']] == ['Selección IA (demo)']
    assert client.get(DIRECTORY, headers=admin, params={'search': '%'}).json()['items'] == []
    assert 'email' not in filtered.text


def test_directory_tracks_expiry_revocation_rotation_and_consumption(client, db):
    admin, staff = login(client, ADMIN), login(client, SEL_IA)
    before = db.scalar(select(func.count()).select_from(RoleAssignment))

    def current():
        response = client.get(DIRECTORY, headers=admin, params={'search': 'Selección IA'})
        assert response.status_code == 200 and response.headers['cache-control'] == 'no-store'
        [account] = response.json()['items']
        return account

    account = current()
    issued = client.post(INVITATIONS, headers=admin, json={'user_id': account['user_id'], 'expires_hours': 2})
    assert issued.status_code == 201
    first = issued.json()
    invite = db.get(Invitation, uuid.UUID(first['invitation']['id']))
    invite.created_at, invite.expires_at = utcnow() - timedelta(hours=3), utcnow() - timedelta(hours=1)
    db.commit()
    assert current()['latest_invitation']['id'] == str(invite.id)

    def accept(receipt):
        return client.post(f'{INVITATIONS}/accept', headers=staff, json={'token': receipt['token']})

    assert accept(first).status_code == 400
    second = client.post(f'{INVITATIONS}/{invite.id}/renew', headers=admin, json={}).json()
    second_id = second['invitation']['id']
    visible = current()['latest_invitation']
    assert visible['id'] == second_id and 'token' not in visible and 'token_hash' not in visible
    assert client.post(f'{INVITATIONS}/{second_id}/revoke', headers=admin).status_code == 200
    assert current()['latest_invitation']['revoked_at'] is not None
    assert accept(second).status_code == 400
    third = client.post(f'{INVITATIONS}/{second_id}/renew', headers=admin, json={}).json()
    assert accept(third).status_code == 200
    assert accept(third).status_code == 400
    assert current()['profile_state'] == 'active' and current()['latest_invitation']['used_at'] is not None
    assert db.scalar(select(func.count()).select_from(RoleAssignment)) == before


def test_directory_pagination_preserves_accounts_and_hides_secrets(client):
    admin = login(client, ADMIN)
    full = client.get(DIRECTORY, headers=admin, params={'limit': 50})
    assert full.status_code == 200
    expected = full.json()['items']
    assert len(expected) >= 2 and not full.json()['has_more']
    issued = client.post(INVITATIONS, headers=admin,
                         json={'user_id': expected[0]['user_id'], 'expires_hours': 2})
    assert issued.status_code == 201, issued.text
    secret = issued.json()['token']
    seen = []
    for offset in range(len(expected) + 1):
        response = client.get(DIRECTORY, headers=admin, params={'limit': 1, 'offset': offset})
        assert response.status_code == 200
        assert response.headers['cache-control'] == 'no-store'
        assert secret not in response.text
        page = response.json()
        assert page['has_more'] == (offset + 1 < len(expected))
        assert len(page['items']) == (1 if offset < len(expected) else 0)
        for account in page['items']:
            seen.append(account['user_id'])
            invitation = account['latest_invitation']
            if invitation is not None:
                assert 'token' not in invitation and 'token_hash' not in invitation
    assert seen == [account['user_id'] for account in expected]
    assert len(seen) == len(set(seen))
