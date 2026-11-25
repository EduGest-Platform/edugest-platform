import uuid
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.modules.staff.application_policy import application_blockers, require_matching_confirmation
from app.modules.staff.application_schemas import AccessApply


def context():
    target = uuid.uuid4()
    actor = SimpleNamespace(user=SimpleNamespace(id=uuid.uuid4()))
    user = SimpleNamespace(id=target, is_active=True, person_id=None)
    profile = SimpleNamespace(user_id=target, state='active')
    row = SimpleNamespace(requested_by=target, requested_role='docente', scope_type='cohort', scope_id='COH-IA',
                          state='approved', reviewed_by=actor.user.id, reviewed_at=datetime.now(timezone.utc))
    return actor, user, profile, row


@pytest.mark.parametrize('changes', [{'confirm': False}, {'confirm': 1}, {'confirm': 'true'},
    {'requested_role': 'coder'}, {'scope_type': 'global', 'scope_id': 'COH-IA'}, {'reviewed_by': str(uuid.uuid4())}])
def test_apply_requires_explicit_boolean_confirmation_and_cannot_spoof_review(changes):
    with pytest.raises(ValidationError):
        AccessApply(**({'confirm': True, 'requested_role': 'docente', 'scope_type': 'cohort', 'scope_id': 'COH-IA'} | changes))


def test_confirmation_echo_must_match_the_stored_role_and_scope():
    _, _, _, row = context()
    body = AccessApply(confirm=True, requested_role='docente', scope_type='cohort', scope_id='COH-IA')
    require_matching_confirmation(row, body)
    body.scope_id = 'COH-DATA'
    with pytest.raises(HTTPException) as error:
        require_matching_confirmation(row, body)
    assert error.value.status_code == 409


@pytest.mark.parametrize('problem,expected', [
    (None, None), ('state', 'request_not_approved'), ('inactive', 'staff_account_required'),
    ('person', 'staff_account_required'), ('profile', 'active_staff_profile_required'),
    ('owner', 'invalid_request_owner'), ('reviewer', 'invalid_review'), ('review_time', 'invalid_review'),
    ('self', 'self_application'), ('scope', 'scope_not_found'), ('existing', 'active_assignment_exists'),
])
def test_preflight_is_conservative_without_granting_or_borrowing_access(problem, expected):
    actor, user, profile, row = context()
    if problem == 'state':
        row.state = 'requested'
    elif problem == 'inactive':
        user.is_active = False
    elif problem == 'person':
        user.person_id = uuid.uuid4()
    elif problem == 'profile':
        profile.state = 'inactive'
    elif problem == 'owner':
        row.requested_by = uuid.uuid4()
    elif problem == 'reviewer':
        row.reviewed_by = row.requested_by
    elif problem == 'review_time':
        row.reviewed_at = None
    elif problem == 'self':
        actor.user.id = row.requested_by
    result = application_blockers(actor, user, profile, row, problem != 'scope', object() if problem == 'existing' else None)
    assert result == ([] if expected is None else [expected])


def test_user_lock_serializes_eligibility_without_conflicting_with_fk_key_share():
    from sqlalchemy.dialects import postgresql
    from app.modules.identity.models import User
    from app.modules.staff.application_service import lock_query

    query = lock_query(User, uuid.uuid4(), user=True)
    assert str(query.compile(dialect=postgresql.dialect())).endswith('FOR NO KEY UPDATE')
    assert query.get_execution_options()['populate_existing'] is True


def test_status_does_not_verify_another_users_or_another_roles_assignment():
    from app.modules.staff.application_service import application_out

    _, _, profile, row = context()
    row.id, row.applied_assignment_id, row.state = uuid.uuid4(), uuid.uuid4(), 'applied'
    grant = SimpleNamespace(id=row.applied_assignment_id, user_id=profile.user_id, role=row.requested_role,
                            scope_type=row.scope_type, scope_id=row.scope_id, revoked_at=None)
    assert application_out(row, profile, grant).assignment_active is True
    grant.user_id = uuid.uuid4()
    result = application_out(row, profile, grant)
    assert result.assignment_id is None and result.assignment_active is None
