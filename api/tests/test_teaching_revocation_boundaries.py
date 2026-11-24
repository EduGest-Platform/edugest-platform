"""KAN-166: API removal from a teaching team must revoke existing sessions in that cohort only."""
import pytest
from sqlalchemy import func, select

from app.modules.identity.models import RoleAssignment, User
from tests.conftest import DOCENTE, SEL_IA, login


def colleague_id(db):
    return db.scalar(select(User.id).where(User.email == SEL_IA))


def change_team(client, headers, user_id, cohort, remove=False):
    path = f'/api/v1/cohorts/{cohort}/teaching-team/{user_id}'
    response = client.delete(path, headers=headers) if remove else client.put(path, headers=headers)
    assert response.status_code == 200, response.text
    return response


@pytest.mark.parametrize('suffix', ['teaching-team', 'attendance-sessions', 'assignments', 'competencies'])
def test_team_removal_revokes_existing_tokens_on_every_academic_surface(client, db, suffix):
    owner = login(client, DOCENTE)
    target = colleague_id(db)
    change_team(client, owner, target, 'COH-IA')
    first, second = login(client, SEL_IA), login(client, SEL_IA)
    path = f'/api/v1/cohorts/COH-IA/{suffix}'
    assert client.get(path, headers=first).status_code == 200
    change_team(client, owner, target, 'COH-IA', remove=True)
    for token in (first, second):
        assert client.get('/api/v1/auth/me', headers=token).status_code == 200
        assert client.get(path, headers=token).status_code == 403
        # Removing teaching access must not revoke the separate selection assignment.
        assert client.get('/api/v1/applications', headers=token).status_code == 200


def test_removing_one_cohort_preserves_the_other_and_blocks_regrant_by_the_removed_teacher(client, db):
    owner = login(client, DOCENTE)
    target = colleague_id(db)
    for cohort in ('COH-IA', 'COH-DATA'):
        change_team(client, owner, target, cohort)
    token = login(client, SEL_IA)
    change_team(client, owner, target, 'COH-IA', remove=True)
    assert client.get('/api/v1/cohorts/COH-IA/teaching-team', headers=token).status_code == 403
    assert client.get('/api/v1/cohorts/COH-DATA/teaching-team', headers=token).status_code == 200
    response = client.put(f'/api/v1/cohorts/COH-IA/teaching-team/{target}', headers=token)
    assert response.status_code == 403
    db.expire_all()
    role = db.scalar(select(RoleAssignment).where(RoleAssignment.user_id == target, RoleAssignment.scope_id == 'COH-IA'))
    assert role.revoked_at is not None


def test_authorized_reactivation_restores_the_same_token_without_duplicate_assignments(client, db):
    owner = login(client, DOCENTE)
    target = colleague_id(db)
    change_team(client, owner, target, 'COH-IA')
    token = login(client, SEL_IA)
    change_team(client, owner, target, 'COH-IA', remove=True)
    assert client.get('/api/v1/cohorts/COH-IA/attendance-sessions', headers=token).status_code == 403
    change_team(client, owner, target, 'COH-IA')
    assert client.get('/api/v1/cohorts/COH-IA/attendance-sessions', headers=token).status_code == 200
    count = db.scalar(select(func.count()).select_from(RoleAssignment).where(
        RoleAssignment.user_id == target, RoleAssignment.role == 'docente', RoleAssignment.scope_id == 'COH-IA'))
    assert count == 1
