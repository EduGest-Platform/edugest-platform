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
