from datetime import timedelta

from sqlalchemy import select

from app.core import audit
from app.core.db import utcnow
from app.core.errors import UserFacingError
from app.core.security import new_token
from app.modules.identity.models import User
from app.modules.staff.models import Invitation, StaffProfile
from app.modules.staff.policy import require_admin, require_staff_account
from app.modules.staff.schemas import InvitationIssued, InvitationOut


def invitation_out(row):
    return InvitationOut.model_validate(row, from_attributes=True)


def eligible_profile(db, profile):
    require_staff_account(db.get(User, profile.user_id))
    if profile.state == 'inactive':
        raise UserFacingError(409, 'staff_profile_inactive', 'La ficha está desactivada y no puede activarse mediante una invitación.')


def locked_invitation(db, actor, invitation_id):
    require_admin(actor)
    profile_id = db.scalar(select(Invitation.staff_profile_id).where(Invitation.id == invitation_id))
    if profile_id is None:
        raise UserFacingError(404, 'invitation_not_found', 'No encontramos esta invitación.')
    profile = db.scalar(select(StaffProfile).where(StaffProfile.id == profile_id).with_for_update())
    row = db.scalar(select(Invitation).where(Invitation.id == invitation_id).with_for_update())
    return profile, row


def issue(db, actor, profile, hours):
    eligible_profile(db, profile)
    now = utcnow()
    pending = db.scalars(select(Invitation).where(Invitation.staff_profile_id == profile.id,
                         Invitation.used_at.is_(None), Invitation.revoked_at.is_(None)).order_by(Invitation.id).with_for_update())
    for old in pending:
        old.revoked_at = now
    token, digest = new_token()
    row = Invitation(staff_profile_id=profile.id, token_hash=digest, created_by=actor.user.id,
                     created_at=now, expires_at=now + timedelta(hours=hours))
    db.add(row)
    db.flush()
    audit.record(db, actor, 'staff.invitation_issued', 'staff_invitation', str(row.id), staff_profile_id=str(profile.id))
    db.commit()
    return InvitationIssued(invitation=invitation_out(row), token=token)


def create_invitation(db, actor, body):
    require_admin(actor)
    user = db.scalar(select(User).where(User.id == body.user_id).with_for_update())
    require_staff_account(user)
    profile = db.scalar(select(StaffProfile).where(StaffProfile.user_id == user.id).with_for_update())
    if profile is None:
        profile = StaffProfile(user_id=user.id, created_by=actor.user.id)
        db.add(profile)
        db.flush()
    return issue(db, actor, profile, body.expires_hours)


def renew_invitation(db, actor, invitation_id, body):
    profile, row = locked_invitation(db, actor, invitation_id)
    if row.used_at is not None:
        raise UserFacingError(409, 'invitation_consumed', 'Esta invitación ya se utilizó.')
    return issue(db, actor, profile, body.expires_hours)


def revoke_invitation(db, actor, invitation_id):
    profile, row = locked_invitation(db, actor, invitation_id)
    if row.used_at is not None:
        raise UserFacingError(409, 'invitation_consumed', 'Esta invitación ya se utilizó.')
    if row.revoked_at is None:
        row.revoked_at = utcnow()
        audit.record(db, actor, 'staff.invitation_revoked', 'staff_invitation', str(row.id), staff_profile_id=str(profile.id))
    db.commit()
    return invitation_out(row)
