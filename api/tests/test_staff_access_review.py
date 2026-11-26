from sqlalchemy import func, select

from app.modules.identity.models import RoleAssignment
from tests.conftest import ADMIN, CAPT_IA, SEL_IA, login
from tests.test_staff_issuance import issue


def active_profile(client, db, account):
    receipt = issue(client, db, login(client, ADMIN), account).json()
    owner = login(client, account)
    response = client.post('/api/v1/staff/invitations/accept', headers=owner, json={'token': receipt['token']})
    assert response.status_code == 200
    return owner


def request(client, headers):
    response = client.post('/api/v1/staff/access-requests', headers=headers, json={
        'requested_role': 'docente', 'scope_type': 'cohort', 'scope_id': 'COH-IA'})
    assert response.status_code == 201
    return response.json()


def test_administrative_review_does_not_apply_a_role(client, db):
    owner = active_profile(client, db, SEL_IA)
    row = request(client, owner)
    before = db.scalar(select(func.count()).select_from(RoleAssignment))
    response = client.post('/api/v1/staff/access-requests/' + row['id'] + '/review', headers=login(client, ADMIN), json={'approved': True})
    assert response.status_code == 200 and response.json()['state'] == 'approved'
    assert response.json()['applied_assignment_id'] is None
    assert db.scalar(select(func.count()).select_from(RoleAssignment)) == before


def test_administrator_cannot_review_own_request(client, db):
    owner = active_profile(client, db, ADMIN)
    row = request(client, owner)
    response = client.post('/api/v1/staff/access-requests/' + row['id'] + '/review', headers=owner, json={'approved': True})
    assert response.status_code == 403 and response.json()['code'] == 'access_self_review'


def test_staff_request_listing_is_own_profile_only(client, db):
    one, two = active_profile(client, db, SEL_IA), active_profile(client, db, CAPT_IA)
    first, second = request(client, one), request(client, two)
    assert [r['id'] for r in client.get('/api/v1/staff/access-requests', headers=one).json()['items']] == [first['id']]
    assert [r['id'] for r in client.get('/api/v1/staff/access-requests', headers=two).json()['items']] == [second['id']]
    assert client.get('/api/v1/staff/access-requests', headers=login(client, ADMIN)).json()['total'] == 2


def test_admin_queue_filters_pending_and_shows_requester_name(client, db):
    owner = active_profile(client, db, SEL_IA)
    approved = request(client, owner)
    pending = request(client, owner)
    admin = login(client, ADMIN)
    path = '/api/v1/staff/access-requests'
    assert client.post(path + '/' + approved['id'] + '/review', headers=admin, json={'approved': True}).status_code == 200
    response = client.get(path, headers=admin, params={'pending_only': True, 'limit': 1})
    assert response.status_code == 200
    [item] = response.json()['items']
    assert response.json()['total'] == 1 and item['id'] == pending['id']
    assert item['requested_by_name'] == client.get('/api/v1/auth/me', headers=owner).json()['display_name']


def test_pending_filter_preserves_own_profile_boundary(client, db):
    owner = active_profile(client, db, SEL_IA)
    other = active_profile(client, db, CAPT_IA)
    approved = request(client, owner)
    pending = request(client, owner)
    request(client, other)
    path = '/api/v1/staff/access-requests'
    admin = login(client, ADMIN)
    reviewed = client.post(path + '/' + approved['id'] + '/review', headers=admin, json={'approved': True})
    assert reviewed.status_code == 200
    name = client.get('/api/v1/auth/me', headers=owner).json()['display_name']
    assert pending['requested_by_name'] == name
    assert reviewed.json()['requested_by_name'] == name
    response = client.get(path, headers=owner, params={'pending_only': True})
    assert response.status_code == 200
    assert response.json()['total'] == 1
    assert [item['id'] for item in response.json()['items']] == [pending['id']]
    response = client.get(path, headers=owner)
    assert response.status_code == 200
    assert response.json()['total'] == 2
    assert [item['id'] for item in response.json()['items']] == [pending['id'], approved['id']]
