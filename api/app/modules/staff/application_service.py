from sqlalchemy import func, select

from app.core import audit
from app.core.authz import Scope
from app.core.errors import UserFacingError
from app.modules.catalog.models import Call, Cohort, Program
from app.modules.identity.models import RoleAssignment, User
from app.modules.staff.application_policy import application_blockers, assignment_matches, request_tuple, require_matching_confirmation
from app.modules.staff.application_schemas import AccessApplicationOut, AccessApplicationPreview
from app.modules.staff.assignment_history import end_assignment
from app.modules.staff.models import AccessChangeRequest, StaffProfile
from app.modules.staff.policy import require_admin
from app.modules.staff.schemas import AccessRequestCreate
from app.modules.staff.service import active_own_profile


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


def lock_query(model, identity, user=False):
    query = select(model).where(model.id == identity)
    # PostgreSQL NO KEY UPDATE serializes user changes but permits FK KEY SHARE checks.
    return query.with_for_update(key_share=user).execution_options(populate_existing=True)


def locked_application(db, actor, request_id):
    require_admin(actor)
    hint, initial_profile = request_profile(db, request_id)
    expected = (hint.staff_profile_id, initial_profile.user_id, *request_tuple(hint))
    model = {'program': Program, 'call': Call, 'cohort': Cohort}.get(hint.scope_type)
    if model is not None:
        query = select(model).where(model.id == hint.scope_id)
        # Cohort first shares the teaching-team writer's serialization point.
        db.scalar(query.with_for_update() if model is Cohort else query.with_for_update(read=True, key_share=True))
    user = db.scalar(lock_query(User, initial_profile.user_id, user=True))
    profile = db.scalar(lock_query(StaffProfile, initial_profile.id))
    row = db.scalar(lock_query(AccessChangeRequest, request_id))
    if row is None or profile is None:
        raise request_not_found()
    if (row.staff_profile_id, profile.user_id, *request_tuple(row)) != expected:
        raise UserFacingError(409, 'access_request_changed', 'La solicitud ha cambiado. Actualiza sus datos antes de aplicarla.')
    return row, profile, user


def application_out(row, profile, assignment):
    verified = assignment_matches(row, profile, assignment)
    active = assignment.revoked_at is None if verified else None
    return AccessApplicationOut(request_id=row.id, request_state=row.state,
                                assignment_id=row.applied_assignment_id if verified else None, assignment_active=active)


def read_application(db, actor, request_id):
    if actor.can('staff.manage', Scope()):
        row, profile = request_profile(db, request_id)
    else:
        profile = active_own_profile(db, actor)
        row = db.scalar(select(AccessChangeRequest).where(AccessChangeRequest.id == request_id,
                                                        AccessChangeRequest.staff_profile_id == profile.id))
        if row is None:
            raise request_not_found()
    assignment = db.get(RoleAssignment, row.applied_assignment_id) if row.applied_assignment_id else None
    result = application_out(row, profile, assignment)
    audit.record(db, actor, 'staff.access_application_viewed', 'access_change_request', str(row.id))
    db.commit()
    return result


def apply_access(db, actor, request_id, body):
    row, profile, user = locked_application(db, actor, request_id)
    require_matching_confirmation(row, body)
    if actor.user.id == row.requested_by:
        raise UserFacingError(403, 'access_self_application', 'Otra persona administradora debe aplicar esta solicitud.')
    if row.state == 'applied':
        assignment = db.get(RoleAssignment, row.applied_assignment_id)
        if not assignment_matches(row, profile, assignment):
            raise UserFacingError(409, 'access_assignment_mismatch', 'No podemos verificar la asignación aplicada. Revisa su trazabilidad antes de continuar.')
        result = application_out(row, profile, assignment)
        db.commit()
        return result
    blockers = blockers_for(db, actor, row, profile, user)
    if blockers:
        raise UserFacingError(409, 'access_application_blocked', 'No se puede aplicar esta solicitud. Actualiza la previsualización y revisa sus bloqueos.')
    assignment = RoleAssignment(user_id=profile.user_id, role=row.requested_role,
                                scope_type=row.scope_type, scope_id=row.scope_id, granted_by=actor.user.id)
    db.add(assignment)
    db.flush()
    row.state, row.applied_assignment_id = 'applied', assignment.id
    audit.record(db, actor, 'staff.access_applied', 'access_change_request', str(row.id),
                 assignment_id=str(assignment.id), role=row.requested_role, scope_type=row.scope_type, scope_id=row.scope_id)
    db.commit()
    return application_out(row, profile, assignment)


def revoke_access(db, actor, request_id, body):
    require_admin(actor)
    # Recheck global authority after serializing revocations, including two admins acting on each other.
    db.execute(select(func.pg_advisory_xact_lock(func.hashtext('staff.access_revocation'))))
    admin_id = db.scalar(select(RoleAssignment.id).where(
        RoleAssignment.user_id == actor.user.id, RoleAssignment.role == 'admin',
        RoleAssignment.scope_type == 'global', RoleAssignment.revoked_at.is_(None),
    ).limit(1))
    if admin_id is None:
        raise UserFacingError(403, 'access_revocation_permission', 'Se requiere una asignación activa de administración global.')
    row, profile, _ = locked_application(db, actor, request_id)
    require_matching_confirmation(row, body)
    if profile.user_id == actor.user.id:
        raise UserFacingError(403, 'access_self_revocation', 'Otra persona administradora debe revocar este acceso.')
    if row.state not in ('applied', 'revoked') or row.applied_assignment_id != body.assignment_id:
        raise UserFacingError(409, 'access_revocation_conflict', 'La asignación confirmada ya no corresponde a esta solicitud.')
    assignment = db.scalar(lock_query(RoleAssignment, body.assignment_id))
    if not assignment_matches(row, profile, assignment):
        raise UserFacingError(409, 'access_assignment_mismatch', 'No podemos verificar la asignación vinculada.')
    if row.state == 'revoked':
        if assignment.revoked_at is None:
            raise UserFacingError(409, 'access_assignment_mismatch', 'La asignación vinculada ya no coincide con la revocación.')
        return application_out(row, profile, assignment)
    if assignment.revoked_at is None and row.requested_role == 'docente' and row.scope_type == 'cohort':
        another_teacher = db.scalar(select(RoleAssignment.id).where(
            RoleAssignment.role == 'docente', RoleAssignment.scope_type == 'cohort', RoleAssignment.scope_id == row.scope_id,
            RoleAssignment.id != assignment.id, RoleAssignment.revoked_at.is_(None),
        ).limit(1))
        if another_teacher is None:
            raise UserFacingError(409, 'last_teacher', 'Añade a otra persona docente a la cohorte antes de retirar este permiso.')
    end_assignment(db, assignment)
    audit.record(db, actor, 'staff.access_revoked', 'access_change_request', str(row.id),
                 assignment_id=str(assignment.id), role=row.requested_role, scope_type=row.scope_type, scope_id=row.scope_id)
    result = application_out(row, profile, assignment)
    db.commit()
    return result
