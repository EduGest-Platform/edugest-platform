from datetime import timedelta

from sqlalchemy import select

from app.core import audit
from app.core.db import utcnow
from app.core.errors import UserFacingError
from app.core.security import new_token, token_hash
from app.modules.identity.models import User
from app.modules.staff.models import Invitation, StaffProfile
from app.modules.staff.policy import invitation_available, require_admin, require_staff_account
from app.modules.staff.schemas import InvitationIssued, InvitationOut, StaffProfileOut


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


def unavailable():
    return UserFacingError(400, 'invitation_unavailable', 'La invitación no está disponible para esta cuenta. Solicita una nueva a administración.')


def accept_invitation(db, actor, body):
    require_staff_account(actor.user)
    digest = token_hash(body.token.get_secret_value())
    profile_id = db.scalar(select(Invitation.staff_profile_id).where(Invitation.token_hash == digest))
    if profile_id is None:
        raise unavailable()
    # All token state transitions use profile -> invitation locking, including rotation/revocation.
    profile = db.scalar(select(StaffProfile).where(StaffProfile.id == profile_id).with_for_update())
    row = db.scalar(select(Invitation).where(Invitation.token_hash == digest).with_for_update())
    now = utcnow()
    if profile is None or profile.user_id != actor.user.id or profile.state == 'inactive' or not invitation_available(row, now):
        raise unavailable()
    eligible_profile(db, profile)
    row.used_at = now
    profile.state = 'active'
    audit.record(db, actor, 'staff.invitation_accepted', 'staff_invitation', str(row.id), staff_profile_id=str(profile.id))
    db.commit()
    return StaffProfileOut.model_validate(profile, from_attributes=True)


def own_profile(db, actor):
    require_staff_account(actor.user)
    profile = db.scalar(select(StaffProfile).where(StaffProfile.user_id == actor.user.id))
    if profile is None:
        raise UserFacingError(404, 'staff_profile_not_found', 'No encontramos una ficha interna para esta cuenta.')
    return StaffProfileOut.model_validate(profile, from_attributes=True)
