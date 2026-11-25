from app.core.errors import UserFacingError


def request_tuple(row):
    return row.requested_role, row.scope_type, row.scope_id


def require_matching_confirmation(row, body):
    if request_tuple(row) != request_tuple(body):
        raise UserFacingError(409, 'access_confirmation_mismatch', 'La confirmación no coincide con el rol y ámbito solicitados. Actualiza la solicitud antes de continuar.')


def application_blockers(actor, user, profile, row, scope_exists, active_assignment):
    blockers = []
    if row.state != 'approved':
        blockers.append('request_not_approved')
    if user is None or not user.is_active or user.person_id is not None:
        blockers.append('staff_account_required')
    if profile.state != 'active':
        blockers.append('active_staff_profile_required')
    if row.requested_by != profile.user_id:
        blockers.append('invalid_request_owner')
    if row.reviewed_by is None or row.reviewed_at is None or row.reviewed_by == row.requested_by:
        blockers.append('invalid_review')
    if actor.user.id == row.requested_by:
        blockers.append('self_application')
    if not scope_exists:
        blockers.append('scope_not_found')
    if active_assignment is not None:
        blockers.append('active_assignment_exists')
    return blockers
