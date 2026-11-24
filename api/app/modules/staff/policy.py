"""Existing global administrative authority only; no new invitation grants."""
from datetime import timezone

from app.core.authz import Scope
from app.core.errors import UserFacingError


def require_admin(actor):
    # Scope() deliberately prevents a program/call wildcard from becoming global administration.
    actor.require('staff.manage', Scope())


def require_staff_account(user):
    if user is None or not user.is_active or user.person_id is not None:
        raise UserFacingError(409, 'staff_account_required', 'Se requiere una cuenta interna activa, sin identidad de aspirante o coder.')


def invitation_available(invitation, now):
    if invitation is None or invitation.used_at is not None or invitation.revoked_at is not None:
        return False
    if now.utcoffset() is None or invitation.expires_at.utcoffset() is None:
        return False
    return now.astimezone(timezone.utc) < invitation.expires_at.astimezone(timezone.utc)


def require_distinct_reviewer(actor, requested_by):
    if actor.user.id == requested_by:
        raise UserFacingError(403, 'access_self_review', 'Otra persona administradora debe revisar esta solicitud.')
