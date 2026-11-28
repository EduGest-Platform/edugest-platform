from types import SimpleNamespace

import pytest

from app.core.authz import EMAIL_SEND_PERMISSION, Principal, Scope


@pytest.mark.parametrize("role,scope_type,scope_id,allowed", [
    ("admin", "global", None, True),
    ("admin", "cohort", "cohort-a", True),
    ("admin", "cohort", "cohort-b", False),
    ("docente", "cohort", "cohort-a", True),
    ("docente", "cohort", "cohort-b", False),
    ("docente", "global", None, False),
    ("docente", "program", "program-a", False),
    ("docente", "call", "call-a", False),
    ("coordinacion", "cohort", "cohort-a", False),
    ("captacion", "cohort", "cohort-a", False),
    ("seleccion", "cohort", "cohort-a", False),
    ("estudiante", "cohort", "cohort-a", False),
])
def test_email_permission_is_scoped(role, scope_type, scope_id, allowed):
    principal = Principal(
        user=SimpleNamespace(),
        assignments=[SimpleNamespace(role=role, scope_type=scope_type, scope_id=scope_id)],
    )
    scope = Scope(program_id="program-a", call_id="call-a", cohort_id="cohort-a")
    assert principal.can(EMAIL_SEND_PERMISSION, scope) is allowed


def test_user_without_assignments_cannot_send_email():
    principal = Principal(user=SimpleNamespace())
    assert not principal.can(EMAIL_SEND_PERMISSION, Scope(cohort_id="cohort-a"))


def test_teacher_can_still_record_attendance_in_program_scope():
    principal = Principal(
        user=SimpleNamespace(),
        assignments=[SimpleNamespace(role="docente", scope_type="program", scope_id="program-a")],
    )
    scope = Scope(program_id="program-a", cohort_id="cohort-a")
    assert principal.can("attendance.record", scope)
    assert not principal.can(EMAIL_SEND_PERMISSION, scope)
