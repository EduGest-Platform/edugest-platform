"""Server-side authorisation: permission = role + scope. Hiding buttons in the UI is never enough."""

from dataclasses import dataclass, field

from fastapi import HTTPException, status

from app.modules.identity.models import RoleAssignment, User

ROLE_PERMISSIONS: dict[str, set[str]] = {
    "admin": {"*"},
    # Fundación / captación: expedientes and CRM of pre-selection.
    "captacion": {"applications.read", "applications.crm", "calls.aggregate"},
    # Colaborador de selección: reads and annotates applications in its call.
    "seleccion": {"applications.read", "applications.crm", "calls.aggregate"},
    # Coordinación: aggregated indicators only, never nominal records.
    "coordinacion": {"calls.aggregate"},
    # Docente: academic permissions arrive in F3 (cohort scope). No access to admissions.
    "docente": set(),
}


@dataclass(frozen=True)
class Scope:
    program_id: str | None = None
    call_id: str | None = None
    cohort_id: str | None = None


@dataclass
class Principal:
    user: User
    assignments: list[RoleAssignment] = field(default_factory=list)

    @property
    def roles(self) -> list[str]:
        return sorted({a.role for a in self.assignments})

    def _grants(self, a: RoleAssignment, perm: str) -> bool:
        perms = ROLE_PERMISSIONS.get(a.role, set())
        return "*" in perms or perm in perms

    def can(self, perm: str, scope: Scope) -> bool:
        for a in self.assignments:
            if not self._grants(a, perm):
                continue
            if a.scope_type == "global":
                return True
            if a.scope_type == "program" and a.scope_id == scope.program_id:
                return True
            if a.scope_type == "call" and a.scope_id == scope.call_id:
                return True
            if a.scope_type == "cohort" and a.scope_id == scope.cohort_id:
                return True
        return False

    def scopes_for(self, perm: str) -> tuple[bool, set[str], set[str]]:
        """(global?, program_ids, call_ids) where `perm` is granted. Used to filter list queries."""
        is_global, programs, calls = False, set(), set()
        for a in self.assignments:
            if not self._grants(a, perm):
                continue
            if a.scope_type == "global":
                is_global = True
            elif a.scope_type == "program":
                programs.add(a.scope_id)
            elif a.scope_type == "call":
                calls.add(a.scope_id)
        return is_global, programs, calls

    def require(self, perm: str, scope: Scope) -> None:
        if not self.can(perm, scope):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "No tienes permiso sobre este ámbito")
