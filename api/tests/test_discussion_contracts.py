"""Offline validation and conservative permission tests; no DB or grants."""
import uuid
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.core.authz import Principal
from app.modules.discussions.access import require_scope
from app.modules.discussions.schemas import CommentCreate, CommentEdit, ThreadCreate, ThreadScope
from app.modules.identity.models import RoleAssignment


@pytest.mark.parametrize('value', [
    {'scope_type': 'application'}, {'scope_type': 'program'},
    {'scope_type': 'program', 'program_id': 'P-IA', 'application_id': str(uuid.uuid4())},
    {'scope_type': 'public', 'program_id': 'P-IA'},
])
def test_scope_is_exactly_one_known_target(value):
    with pytest.raises(ValidationError):
        ThreadScope(**value)


def test_content_is_trimmed_before_validation_and_does_not_accept_actor_fields():
    assert CommentCreate(body='  Synthetic text  ').body == 'Synthetic text'
    assert ThreadCreate(scope_type='program', program_id='P-IA', subject='  Topic  ').subject == 'Topic'
    for constructor, value in [(CommentCreate, {'body': '  '}), (CommentCreate, {'body': 'text', 'actor_user_id': str(uuid.uuid4())}),
                               (CommentEdit, {'body': 'text', 'expected_version': 0})]:
        with pytest.raises(ValidationError):
            constructor(**value)


@pytest.mark.parametrize(('role', 'scope_type', 'scope_id', 'allowed'), [
    ('admin', 'global', None, True), ('captacion', 'program', 'P-IA', True),
    ('seleccion', 'call', 'CALL-IA', False), ('captacion', 'program', 'P-DATA', False),
    ('docente', 'cohort', 'COH-IA', False),
])
def test_call_or_cohort_authority_is_not_broadened_to_program_discussions(role, scope_type, scope_id, allowed):
    actor = Principal(user=SimpleNamespace(), assignments=[RoleAssignment(role=role, scope_type=scope_type, scope_id=scope_id)])
    class Database:
        def get(self, model, key):
            assert allowed, 'Denied program scopes must not look up the target'
            return SimpleNamespace(id=key)
    scope = ThreadScope(scope_type='program', program_id='P-IA')
    if allowed:
        require_scope(Database(), actor, scope, write=True)
    else:
        with pytest.raises(HTTPException) as error:
            require_scope(Database(), actor, scope, write=True)
        assert error.value.status_code == 403
