import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.core.authz import Principal
from app.modules.identity.models import RoleAssignment
from app.modules.staff.policy import invitation_available, require_admin, require_staff_account
from app.modules.staff.schemas import AccessRequestCreate, InvitationAccept, InvitationCreate


@pytest.mark.parametrize(('role', 'kind', 'scope_id', 'allowed'), [
    ('admin', 'global', None, True), ('admin', 'program', 'P-IA', False),
    ('captacion', 'program', 'P-IA', False), ('coordinacion', 'global', None, False),
])
def test_invitation_management_is_global_admin_only(role, kind, scope_id, allowed):
    actor = Principal(user=SimpleNamespace(), assignments=[RoleAssignment(role=role, scope_type=kind, scope_id=scope_id)])
    if allowed:
        require_admin(actor)
    else:
        with pytest.raises(HTTPException):
            require_admin(actor)


@pytest.mark.parametrize('changes', [{'person_id': uuid.uuid4()}, {'is_active': False}])
def test_person_or_inactive_accounts_are_not_staff_invite_targets(changes):
    user = SimpleNamespace(**{'person_id': None, 'is_active': True, **changes})
    with pytest.raises(HTTPException):
        require_staff_account(user)


@pytest.mark.parametrize('delta,available', [(-1, True), (0, False), (1, False)])
def test_expiration_boundary_is_exclusive(delta, available):
    end = datetime(2030, 1, 1, tzinfo=timezone.utc)
    row = SimpleNamespace(used_at=None, revoked_at=None, expires_at=end)
    assert invitation_available(row, end + timedelta(microseconds=delta)) is available


def test_secret_input_repr_is_redacted_and_client_cannot_spoof_actors():
    value = 'synthetic-contract-value-' + 'x' * 32
    assert value not in repr(InvitationAccept(token=value))
    with pytest.raises(ValidationError):
        InvitationCreate(user_id=uuid.uuid4(), created_by=uuid.uuid4())
    with pytest.raises(ValidationError):
        AccessRequestCreate(requested_role='docente', scope_type='global', scope_id='P-IA')
    with pytest.raises(ValidationError):
        InvitationCreate(user_id=uuid.uuid4(), expires_hours=0)
