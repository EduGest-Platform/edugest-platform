"""Which documents a caller may retrieve (ADR-0005, KAN-151). Decided on the server, never taken from the request.

- Staff with knowledge.read: the cohorts inside their scope (global, program, call or cohort), through Principal.can.
- Coders: the cohorts of their ACTIVE enrollments. A coder who left (finalizada, baja_voluntaria) reads nothing.
- Everyone else (captación, selección, applicants): nothing, so the assistant abstains.

The retrieval query applies this scope in SQL before ranking, so a document outside it can never be a candidate.
"""

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.authz import KNOWLEDGE_READ_PERMISSION, Principal
from app.modules.catalog.models import Cohort
from app.modules.learning.access import cohort_scope
from app.modules.learning.models import Enrollment


@dataclass(frozen=True)
class KnowledgeScope:
    cohorts: frozenset[str]
    programs: frozenset[str]

    @property
    def is_empty(self) -> bool:
        return not self.cohorts


def knowledge_scope(db: Session, p: Principal) -> KnowledgeScope:
    cohorts = list(db.scalars(select(Cohort)))
    readable = {c.id for c in cohorts if p.can(KNOWLEDGE_READ_PERMISSION, cohort_scope(c))}
    if p.user.person_id is not None:
        active = select(Enrollment.cohort_id).where(Enrollment.person_id == p.user.person_id, Enrollment.estado == "activa")
        readable |= set(db.scalars(active))
    programs = {c.program_id for c in cohorts if c.id in readable}
    return KnowledgeScope(cohorts=frozenset(readable), programs=frozenset(programs))
