"""PostgreSQL staff persistence constraints; these tables never grant roles automatically."""
from datetime import timedelta

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.core.db import utcnow
from app.modules.identity.models import RoleAssignment, User
from app.modules.staff.models import AccessChangeRequest, Invitation, StaffProfile
from tests.conftest import ADMIN, SEL_IA


def profile(db):
    owner = db.scalar(select(User.id).where(User.email == ADMIN))
    target = db.scalar(select(User.id).where(User.email == SEL_IA))
    result = StaffProfile(user_id=target, created_by=owner)
    db.add(result)
    db.flush()
    return result, owner


def test_profile_and_invitation_do_not_activate_or_grant_roles(db):
    before = db.scalar(select(func.count()).select_from(RoleAssignment))
    staff, owner = profile(db)
    db.add(Invitation(staff_profile_id=staff.id, token_hash='a' * 64, created_by=owner, expires_at=utcnow() + timedelta(days=1)))
    db.commit()
    assert staff.state == 'pending'
    assert db.scalar(select(func.count()).select_from(RoleAssignment)) == before


@pytest.mark.parametrize('invalid', ['expired', 'not_hash', 'used_after_expiry'])
def test_invalid_invitation_evidence_is_rejected(db, invalid):
    staff, owner = profile(db)
    now = utcnow()
    row = Invitation(staff_profile_id=staff.id, token_hash='a' * 64, created_by=owner, created_at=now, expires_at=now + timedelta(hours=1))
    if invalid == 'expired':
        row.expires_at = now
    elif invalid == 'not_hash':
        row.token_hash = 'z' * 64
    else:
        row.used_at = now + timedelta(hours=2)
    db.add(row)
    with pytest.raises(IntegrityError):
        db.flush()
    db.rollback()


def test_self_approval_is_rejected_without_creating_a_role(db):
    staff, owner = profile(db)
    db.add(AccessChangeRequest(staff_profile_id=staff.id, requested_role='docente', scope_type='cohort', scope_id='COH-IA',
                               state='approved', requested_by=owner, reviewed_by=owner, reviewed_at=utcnow()))
    with pytest.raises(IntegrityError):
        db.flush()
    db.rollback()
