"""Capture existing authority at signature time without granting permissions."""
from app.core.authz import Principal, Scope


def signature_authority(actor: Principal, program_id: str, call_id: str) -> list[dict]:
    scope = Scope(program_id=program_id, call_id=call_id)
    grants = {
        (assignment.role, assignment.scope_type, assignment.scope_id)
        for assignment in actor.assignments
        if assignment.revoked_at is None
        and Principal(user=actor.user, assignments=[assignment]).can('selection.decide', scope)
    }
    return [dict(role=role, scope_type=scope_type, scope_id=scope_id, permission='selection.decide')
            for role, scope_type, scope_id in sorted(grants, key=lambda grant: (grant[0], grant[1], grant[2] or ''))]
