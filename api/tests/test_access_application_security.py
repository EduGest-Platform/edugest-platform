"""Offline authorization boundaries; integration coverage lives in the API suite."""
import uuid
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.core.authz import Principal
from app.modules.staff.application_schemas import AccessApply
from app.modules.staff.application_service import apply_access, preview_application


class NoResourceAccess:
    def __getattr__(self, name):
        raise AssertionError(f'Unauthorized resource access: {name}')


@pytest.mark.parametrize('role,scope', [
    ('admin', 'program'), ('admin', 'call'), ('admin', 'cohort'),
    ('captacion', 'global'), ('seleccion', 'global'), ('coordinacion', 'global'),
    ('docente', 'global'), ('coder', 'global'),
])
@pytest.mark.parametrize('operation', ['preview', 'apply'])
def test_non_global_administrators_are_denied_before_loading_a_request(role, scope, operation):
    actor = Principal(SimpleNamespace(id=uuid.uuid4()), [
        SimpleNamespace(role=role, scope_type=scope, scope_id='untrusted-scope')])
    with pytest.raises(HTTPException) as error:
        if operation == 'preview':
            preview_application(NoResourceAccess(), actor, uuid.uuid4())
        else:
            body = AccessApply(confirm=True, requested_role='docente', scope_type='cohort', scope_id='COH-IA')
            apply_access(NoResourceAccess(), actor, uuid.uuid4(), body)
    assert error.value.status_code == 403
