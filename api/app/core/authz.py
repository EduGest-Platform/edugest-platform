"""Server-side authorisation: permission = role + scope. Hiding buttons in the UI is never enough."""

from dataclasses import dataclass, field

from fastapi import HTTPException, status

from app.modules.identity.models import RoleAssignment, User

# Exceptions are visible to, and can be recorded by, every role below; only admissions staff also record met / not met.
REQUIREMENT_EXCEPTION_PERMISSIONS = {"requirements.read", "requirements.exception"}
REQUIREMENT_REVIEW_PERMISSIONS = {*REQUIREMENT_EXCEPTION_PERMISSIONS, "requirements.review"}
# End of pre-selection (KAN-153): the five internal profiles may read and decide, each only inside its own scope.
PRESELECTION_PERMISSIONS = {"preselection.read", "preselection.decide"}
# Admission decision (KAN-48, PO 19/11/2026): selección and coordinación decide by default; administration through the wildcard.
SELECTION_PERMISSIONS = {"selection.read", "selection.decide"}
# Melissa round 3 Q11: only administration (wildcard) changes the selection quorum of a call. No role grant on purpose.
SELECTION_POLICY_PERMISSION = "selection.configure"
# PO decision 19/11/2026: administration (wildcard) and captación edit the per-call silence policy.
PRESELECTION_POLICY_PERMISSION = "preselection.configure"

# Academic follow-up (KAN-55, KAN-57): teachers work only on the cohorts they are assigned to.
ATTENDANCE_PERMISSIONS = {"attendance.read", "attendance.record"}
# PO 19/11/2026: coordination sees cohort attendance totals only, never per-person rows.
ATTENDANCE_AGGREGATE_PERMISSION = "attendance.aggregate"
COMPETENCY_PERMISSIONS = {"competencies.read", "competencies.configure", "competencies.assess"}
SUBMISSION_PERMISSIONS = {"submissions.read", "submissions.review"}
# PO 23/11/2026: like attendance, coordination only sees submission and competency totals, never per-person rows.
SUBMISSION_AGGREGATE_PERMISSION = "submissions.aggregate"
COMPETENCY_AGGREGATE_PERMISSION = "competencies.aggregate"
# Melissa round 3 Q15 (PO approved 23/11/2026): a teacher manages the teaching team of its own cohorts.
TEAM_MANAGE_PERMISSION = "cohort.team.manage"
# Q15: the academic attributions of coordination (cohort indicators) also belong to the teacher of the cohort.
ACADEMIC_AGGREGATE_PERMISSIONS = {ATTENDANCE_AGGREGATE_PERMISSION, SUBMISSION_AGGREGATE_PERMISSION, COMPETENCY_AGGREGATE_PERMISSION}

ROLE_PERMISSIONS: dict[str, set[str]] = {
    "admin": {"*"},
    # Fundación / captación: expedientes and CRM of pre-selection, requirement reviews and exceptions.
    "captacion": {"applications.read", "applications.crm", "calls.aggregate", *REQUIREMENT_REVIEW_PERMISSIONS, *PRESELECTION_PERMISSIONS, PRESELECTION_POLICY_PERMISSION},
    # Colaborador de selección: reads and annotates applications in its call, reviews requirements.
    "seleccion": {"applications.read", "applications.crm", "calls.aggregate", *REQUIREMENT_REVIEW_PERMISSIONS, *PRESELECTION_PERMISSIONS, *SELECTION_PERMISSIONS},
    # Coordinación: aggregated indicators (calls, cohort attendance), plus reading and recording requirement exceptions (KAN-128).
    "coordinacion": {"calls.aggregate", ATTENDANCE_AGGREGATE_PERMISSION, SUBMISSION_AGGREGATE_PERMISSION, COMPETENCY_AGGREGATE_PERMISSION, *REQUIREMENT_EXCEPTION_PERMISSIONS, *PRESELECTION_PERMISSIONS, *SELECTION_PERMISSIONS},
    # Docente: no access to admissions, except reading and recording requirement exceptions (KAN-128).
    # Records attendance, configures/assesses competencies and reviews submissions of its own cohorts (KAN-55, KAN-57, KAN-56).
    # Q15: also the cohort indicators of coordination and the teaching team of its cohorts. Never the admission decision.
    "docente": {*REQUIREMENT_EXCEPTION_PERMISSIONS, *PRESELECTION_PERMISSIONS, *ATTENDANCE_PERMISSIONS, *COMPETENCY_PERMISSIONS, *SUBMISSION_PERMISSIONS,
                *ACADEMIC_AGGREGATE_PERMISSIONS, TEAM_MANAGE_PERMISSION},
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
