"""Offline moderation and immutable-input boundary checks."""
import uuid
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.core.authz import Principal
from app.modules.discussions.schemas import CommentEdit
from app.modules.discussions.service import require_owner_or_moderator
from app.modules.identity.models import RoleAssignment


@pytest.mark.parametrize(('role', 'kind', 'scope_id', 'allowed'), [
    ('admin', 'global', None, True), ('admin', 'program', 'P-IA', True),
    ('admin', 'program', 'P-DATA', False), ('captacion', 'program', 'P-IA', False),
    ('seleccion', 'call', 'CALL-IA', False), ('docente', 'cohort', 'COH-IA', False),
])
def test_moderation_requires_an_existing_matching_wildcard(role, kind, scope_id, allowed):
    actor = Principal(user=SimpleNamespace(id=uuid.uuid4()), assignments=[RoleAssignment(role=role, scope_type=kind, scope_id=scope_id)])
    thread = SimpleNamespace(scope_type='program', application_id=None, program_id='P-IA')
    class Database:
        def get(self, model, key):
            return SimpleNamespace(id=key)
    if allowed:
        require_owner_or_moderator(Database(), actor, thread, uuid.uuid4())
    else:
        with pytest.raises(HTTPException) as error:
            require_owner_or_moderator(Database(), actor, thread, uuid.uuid4())
        assert error.value.status_code == 403


@pytest.mark.parametrize('field', ['parent_id', 'actor_user_id', 'thread_id'])
def test_edit_payload_cannot_reparent_or_impersonate(field):
    with pytest.raises(ValidationError):
        CommentEdit(body='Synthetic allowed edit', expected_version=1, **{field: str(uuid.uuid4())})
