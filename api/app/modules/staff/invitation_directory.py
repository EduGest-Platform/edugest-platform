"""List eligible internal accounts and their latest invitation for global administration."""

from sqlalchemy import select

from app.core import audit
from app.modules.identity.models import User
from app.modules.staff.models import Invitation, StaffProfile
from app.modules.staff.policy import require_admin
from app.modules.staff.schemas import InvitationAccount, InvitationDirectory
from app.modules.staff.service import invitation_out


def list_invitation_accounts(db, actor, search: str, offset: int, limit: int) -> InvitationDirectory:
    require_admin(actor)
    latest = (
        select(Invitation.id).where(Invitation.staff_profile_id == StaffProfile.id)
        .order_by(Invitation.created_at.desc(), Invitation.id.desc())
        .limit(1).correlate(StaffProfile).scalar_subquery()
    )
    query = (
        select(User.id, User.display_name, StaffProfile.state, Invitation)
        .outerjoin(StaffProfile, StaffProfile.user_id == User.id)
        .outerjoin(Invitation, Invitation.id == latest)
        .where(User.is_active.is_(True), User.person_id.is_(None),
               StaffProfile.state.is_(None) | StaffProfile.state.in_(('pending', 'active')))
    )
    if search.strip():
        query = query.where(User.display_name.icontains(search.strip(), autoescape=True))
    rows = db.execute(query.order_by(User.display_name, User.id).offset(offset).limit(limit + 1)).all()
    result = InvitationDirectory(items=[
        InvitationAccount(user_id=user_id, display_name=display_name, profile_state=profile_state,
                          latest_invitation=invitation_out(invite) if invite else None)
        for user_id, display_name, profile_state, invite in rows[:limit]
    ], has_more=len(rows) > limit)
    audit.record(db, actor, 'staff.invitation_directory_viewed', 'staff_invitation', None)
    db.commit()
    return result
