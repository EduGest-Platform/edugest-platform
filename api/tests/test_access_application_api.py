from sqlalchemy import func, select
import uuid

from app.core.db import utcnow
from app.modules.identity.models import RoleAssignment
from app.modules.audit.models import AuditEvent
from tests.conftest import ADMIN, CAPT_IA, SEL_IA, login
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


def confirmation(row):
    return {'confirm': True, 'requested_role': row['requested_role'], 'scope_type': row['scope_type'], 'scope_id': row['scope_id']}


def test_application_grants_exact_scope_once_and_existing_session_sees_the_role(client, db):
    row, owner, admin = approved_request(client, db)
    before = db.scalar(select(func.count()).select_from(RoleAssignment))
    response = client.post(path(row['id']) + '/apply', headers=admin, json=confirmation(row))
    assert response.status_code == 200 and response.json()['assignment_active'] is True
    assert response.json()['request_state'] == 'applied'
    repeated = client.post(path(row['id']) + '/apply', headers=admin, json=confirmation(row))
    assert repeated.status_code == 200 and repeated.json() == response.json()
    assert db.scalar(select(func.count()).select_from(RoleAssignment)) == before + 1
    assert db.scalar(select(func.count()).select_from(AuditEvent).where(AuditEvent.action == 'staff.access_applied')) == 1
    roles = client.get('/api/v1/auth/me', headers=owner).json()['roles']
    assert {'role': 'docente', 'scope_type': 'cohort', 'scope_id': 'COH-IA'} in roles


def test_echo_mismatch_and_non_admin_application_do_not_create_roles(client, db):
    row, owner, admin = approved_request(client, db)
    before = db.scalar(select(func.count()).select_from(RoleAssignment))
    body = confirmation(row)
    assert client.post(path(row['id']) + '/apply', headers=owner, json=body).status_code == 403
    assert client.post(path(row['id']) + '/apply', headers=admin, json={**body, 'scope_id': 'COH-DATA'}).status_code == 409
    assert db.scalar(select(func.count()).select_from(RoleAssignment)) == before


def test_status_is_own_or_global_admin_only(client, db):
    row, owner, admin = approved_request(client, db)
    applied = client.post(path(row['id']) + '/apply', headers=admin, json=confirmation(row))
    assert client.get(path(row['id']) + '/application', headers=owner).json() == applied.json()
    outsider = active_profile(client, db, CAPT_IA)
    assert client.get(path(row['id']) + '/application', headers=outsider).status_code == 404
    assert client.get(path(uuid.uuid4()) + '/application', headers=outsider).status_code == 404


def test_retry_reports_a_revoked_assignment_without_regranting_it(client, db):
    row, owner, admin = approved_request(client, db)
    applied = client.post(path(row['id']) + '/apply', headers=admin, json=confirmation(row)).json()
    grant = db.get(RoleAssignment, uuid.UUID(applied['assignment_id']))
    grant.revoked_at = utcnow()
    db.commit()
    before = db.scalar(select(func.count()).select_from(RoleAssignment))
    status = client.get(path(row['id']) + '/application', headers=owner)
    assert status.status_code == 200 and status.json()['assignment_active'] is False
    retried = client.post(path(row['id']) + '/apply', headers=admin, json=confirmation(row))
    assert retried.status_code == 200 and retried.json() == status.json()
    assert db.scalar(select(func.count()).select_from(RoleAssignment)) == before


def test_existing_grant_is_not_borrowed_by_an_approved_request(client, db):
    row, _, admin = approved_request(client, db)
    from app.modules.staff.models import AccessChangeRequest, StaffProfile

    stored = db.get(AccessChangeRequest, uuid.UUID(row['id']))
    profile = db.get(StaffProfile, stored.staff_profile_id)
    db.add(RoleAssignment(user_id=profile.user_id, role='docente', scope_type='cohort', scope_id='COH-IA'))
    db.commit()
    before = db.scalar(select(func.count()).select_from(RoleAssignment))
    preview = client.get(path(row['id']) + '/application-preview', headers=admin)
    assert preview.status_code == 200
    assert preview.json()['blockers'] == ['active_assignment_exists']
    response = client.post(path(row['id']) + '/apply', headers=admin, json=confirmation(row))
    assert response.status_code == 409
    db.expire_all()
    assert db.get(AccessChangeRequest, stored.id).state == 'approved'
    assert db.get(AccessChangeRequest, stored.id).applied_assignment_id is None
    assert db.scalar(select(func.count()).select_from(RoleAssignment)) == before


def test_two_requests_for_the_same_grant_only_apply_once(client, db):
    row, owner, admin = approved_request(client, db)
    other = request(client, owner)
    reviewed = client.post(path(other['id']) + '/review', headers=admin, json={'approved': True})
    assert reviewed.status_code == 200
    before = db.scalar(select(func.count()).select_from(RoleAssignment))
    assert client.post(path(row['id']) + '/apply', headers=admin, json=confirmation(row)).status_code == 200
    assert client.post(path(other['id']) + '/apply', headers=admin, json=confirmation(other)).status_code == 409
    assert db.scalar(select(func.count()).select_from(RoleAssignment)) == before + 1


def test_application_and_request_roll_back_when_audit_fails(client, db, monkeypatch):
    from fastapi.testclient import TestClient
    from app.core import audit
    from app.main import app
    from app.modules.staff.models import AccessChangeRequest

    row, _, admin = approved_request(client, db)
    before = db.scalar(select(func.count()).select_from(RoleAssignment))
    original = audit.record

    def fail_after_flush(session, actor, action, *args, **kwargs):
        if action == 'staff.access_applied':
            session.flush()
            raise RuntimeError('Synthetic audit failure')
        return original(session, actor, action, *args, **kwargs)

    monkeypatch.setattr(audit, 'record', fail_after_flush)
    with TestClient(app, raise_server_exceptions=False) as isolated:
        response = isolated.post(path(row['id']) + '/apply', headers=admin, json=confirmation(row))
    assert response.status_code == 500
    db.expire_all()
    stored = db.get(AccessChangeRequest, uuid.UUID(row['id']))
    assert stored.state == 'approved' and stored.applied_assignment_id is None
    assert db.scalar(select(func.count()).select_from(RoleAssignment)) == before


def test_application_user_lock_allows_concurrent_request_foreign_key_check(client, db, monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event
    from fastapi.testclient import TestClient
    from sqlalchemy import text
    from app.core.db import SessionLocal
    from app.main import app
    from app.modules.staff import application_service
    from app.modules.staff.models import AccessChangeRequest, StaffProfile

    row, _, admin = approved_request(client, db)
    stored = db.get(AccessChangeRequest, uuid.UUID(row['id']))
    profile_id = stored.staff_profile_id
    user_lock_acquired = Event()
    original = application_service.lock_query

    def observed_lock(model, identity, user=False):
        if model is StaffProfile:
            # The preceding scalar call has already acquired the user lock.
            user_lock_acquired.set()
        return original(model, identity, user=user)

    monkeypatch.setattr(application_service, 'lock_query', observed_lock)

    def apply_in_another_session():
        with TestClient(app) as isolated:
            return isolated.post(path(row['id']) + '/apply', headers=admin, json=confirmation(row))

    with ThreadPoolExecutor(max_workers=1) as executor:
        with SessionLocal() as writer:
            writer.execute(text("SET LOCAL lock_timeout = '3s'"))
            profile = writer.scalar(select(StaffProfile).where(StaffProfile.id == profile_id).with_for_update())
            future = executor.submit(apply_in_another_session)
            assert user_lock_acquired.wait(10), 'Application did not reach the profile lock'
            # Simulate request creation: profile lock followed by a User FK check.
            writer.add(AccessChangeRequest(staff_profile_id=profile.id, requested_by=profile.user_id,
                requested_role='docente', scope_type='cohort', scope_id='COH-IA', state='requested'))
            writer.flush()
            writer.commit()
        response = future.result(timeout=15)
    assert response.status_code == 200
