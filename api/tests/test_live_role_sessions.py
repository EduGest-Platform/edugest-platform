"""KAN-104: opaque sessions must re-read current authorization on every request."""
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from app.core import deps
from app.core.db import utcnow
from app.core.security import token_hash
from app.modules.identity.models import AuthSession, RoleAssignment, User
from tests.conftest import CAPT_DATA, CAPT_IA, login


def assignments(db):
    user = db.scalar(select(User).where(User.email == CAPT_IA))
    return user, list(db.scalars(select(RoleAssignment).where(RoleAssignment.user_id == user.id)))


def test_revocation_applies_to_existing_sibling_sessions_without_logging_them_out(client, db):
    one, two, other = login(client, CAPT_IA), login(client, CAPT_IA), login(client, CAPT_DATA)
    assert client.get('/api/v1/applications', headers=one).status_code == 200
    user, roles = assignments(db)
    for role in roles:
        role.revoked_at = utcnow()
    db.commit()
    for token in (one, two):
        response = client.get('/api/v1/auth/me', headers=token)
        assert response.status_code == 200 and response.json()['roles'] == []
        assert response.json()['id'] == str(user.id)
        assert client.get('/api/v1/applications', headers=token).status_code == 403
    assert client.get('/api/v1/applications', headers=other).status_code == 200
    for role in roles:
        role.revoked_at = None
    db.commit()
    assert client.get('/api/v1/applications', headers=one).status_code == 200
    assert client.get('/api/v1/applications', headers=two).status_code == 200


def test_new_scoped_grant_and_revocation_are_seen_by_the_same_token(client, db):
    token = login(client, CAPT_IA)
    user, _ = assignments(db)
    path = '/api/v1/cohorts/COH-DATA/attendance-sessions'
    assert client.get(path, headers=token).status_code == 403
    role = RoleAssignment(user_id=user.id, role='docente', scope_type='cohort', scope_id='COH-DATA')
    db.add(role)
    db.commit()
    assert client.get(path, headers=token).status_code == 200
    assert client.get('/api/v1/cohorts/COH-IA/attendance-sessions', headers=token).status_code == 403
    role.revoked_at = utcnow()
    db.commit()
    assert client.get(path, headers=token).status_code == 403
    assert client.get('/api/v1/applications', headers=token).status_code == 200


@pytest.mark.parametrize(('microseconds', 'expected'), [(-1, 200), (0, 401), (1, 401)])
def test_exact_session_expiry_boundary(client, db, monkeypatch, microseconds, expected):
    token = login(client, CAPT_IA)
    digest = token_hash(token['Authorization'].removeprefix('Bearer '))
    session = db.scalar(select(AuthSession).where(AuthSession.token_hash == digest))
    cutoff = datetime(2030, 1, 1, tzinfo=timezone.utc)
    session.expires_at = cutoff
    db.commit()
    monkeypatch.setattr(deps, 'utcnow', lambda: cutoff + timedelta(microseconds=microseconds))
    assert client.get('/api/v1/auth/me', headers=token).status_code == expected
