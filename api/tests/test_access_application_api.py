from sqlalchemy import func, select

from app.modules.identity.models import RoleAssignment
from tests.conftest import ADMIN, SEL_IA, login
from tests.test_staff_access_review import active_profile, request


def approved_request(client, db, account=SEL_IA):
    owner = active_profile(client, db, account)
    requested = request(client, owner)
    admin = login(client, ADMIN)
    reviewed = client.post(path(requested['id']) + '/review', headers=admin, json={'approved': True})
    assert reviewed.status_code == 200 and reviewed.json()['state'] == 'approved'
    return reviewed.json(), owner, admin


def path(request_id):
    return '/api/v1/staff/access-requests/' + str(request_id)


def test_preview_leaves_roles_unchanged_and_owner_cannot_preview_administratively(client, db):
    row, owner, admin = approved_request(client, db)
    before = db.scalar(select(func.count()).select_from(RoleAssignment))
    response = client.get(path(row['id']) + '/application-preview', headers=admin)
    assert response.status_code == 200 and response.json()['can_apply'] is True and response.json()['blockers'] == []
    assert response.json()['requested'] == {'requested_role': 'docente', 'scope_type': 'cohort', 'scope_id': 'COH-IA'}
    assert db.scalar(select(func.count()).select_from(RoleAssignment)) == before
    assert client.get(path(row['id']) + '/application-preview', headers=owner).status_code == 403
