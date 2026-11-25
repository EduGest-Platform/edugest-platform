from sqlalchemy import select

from app.core import audit
from app.core.errors import UserFacingError
from app.modules.catalog.models import Call, Cohort, Program
from app.modules.identity.models import RoleAssignment, User
from app.modules.staff.application_policy import application_blockers
from app.modules.staff.application_schemas import AccessApplicationPreview
from app.modules.staff.models import AccessChangeRequest, StaffProfile
from app.modules.staff.policy import require_admin
from app.modules.staff.schemas import AccessRequestCreate


def request_not_found():
    return UserFacingError(404, 'access_request_not_found', 'No encontramos esta solicitud de acceso.')


def request_profile(db, request_id):
    row = db.get(AccessChangeRequest, request_id)
    profile = db.get(StaffProfile, row.staff_profile_id) if row else None
    if row is None or profile is None:
        raise request_not_found()
    return row, profile


def scope_exists(db, row):
    if row.scope_type == 'global':
        return row.scope_id is None
    model = {'program': Program, 'call': Call, 'cohort': Cohort}.get(row.scope_type)
    return model is not None and db.get(model, row.scope_id) is not None


def active_assignment(db, profile, row):
    return db.scalar(select(RoleAssignment).where(RoleAssignment.user_id == profile.user_id,
        RoleAssignment.role == row.requested_role, RoleAssignment.scope_type == row.scope_type,
        RoleAssignment.scope_id == row.scope_id, RoleAssignment.revoked_at.is_(None)).order_by(RoleAssignment.id).limit(1))


def blockers_for(db, actor, row, profile, user):
    return application_blockers(actor, user, profile, row, scope_exists(db, row), active_assignment(db, profile, row))


def preview_application(db, actor, request_id):
    require_admin(actor)
    row, profile = request_profile(db, request_id)
    blockers = blockers_for(db, actor, row, profile, db.get(User, profile.user_id))
    result = AccessApplicationPreview(request_id=row.id, user_id=profile.user_id,
        requested=AccessRequestCreate(requested_role=row.requested_role, scope_type=row.scope_type, scope_id=row.scope_id),
        can_apply=not blockers, blockers=blockers)
    audit.record(db, actor, 'staff.access_application_previewed', 'access_change_request', str(row.id))
    db.commit()
    return result
