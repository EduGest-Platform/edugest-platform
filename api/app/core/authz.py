"""Server-side authorisation: permission = role + scope. Hiding buttons in the UI is never enough."""

from dataclasses import dataclass, field

from fastapi import HTTPException, status

from app.modules.identity.models import RoleAssignment, User

# Exceptions are visible to, and can be recorded by, every role below; only admissions staff also record met / not met.
REQUIREMENT_EXCEPTION_PERMISSIONS = {"requirements.read", "requirements.exception"}
REQUIREMENT_REVIEW_PERMISSIONS = {*REQUIREMENT_EXCEPTION_PERMISSIONS, "requirements.review"}
# End of pre-selection (KAN-153): the five internal profiles may read and decide, each only inside its own scope.
PRESELECTION_PERMISSIONS = {"preselection.read", "preselection.decide"}
# PO decision 19/11/2026: administration (wildcard) and captación edit the per-call silence policy.
PRESELECTION_POLICY_PERMISSION = "preselection.configure"

ROLE_PERMISSIONS: dict[str, set[str]] = {
    "admin": {"*"},
    # Fundación / captación: expedientes and CRM of pre-selection, requirement reviews and exceptions.
    "captacion": {"applications.read", "applications.crm", "calls.aggregate", *REQUIREMENT_REVIEW_PERMISSIONS, *PRESELECTION_PERMISSIONS, PRESELECTION_POLICY_PERMISSION},
    # Colaborador de selección: reads and annotates applications in its call, reviews requirements.
    "seleccion": {"applications.read", "applications.crm", "calls.aggregate", *REQUIREMENT_REVIEW_PERMISSIONS, *PRESELECTION_PERMISSIONS},
    # Coordinación: aggregated indicators, plus reading and recording requirement exceptions (KAN-128).
    "coordinacion": {"calls.aggregate", *REQUIREMENT_EXCEPTION_PERMISSIONS, *PRESELECTION_PERMISSIONS},
    # Docente: no access to admissions, except reading and recording requirement exceptions (KAN-128).
    "docente": {*REQUIREMENT_EXCEPTION_PERMISSIONS, *PRESELECTION_PERMISSIONS},
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
