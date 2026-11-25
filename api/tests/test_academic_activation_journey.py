"""HTTP evidence for cohort activation and its downstream academic records."""

from sqlalchemy import select

from app.modules.audit.models import AuditEvent
from app.modules.catalog.models import Cohort
from app.modules.competencies.models import CohortCompetencyFramework
from app.modules.identity.models import User
from tests.conftest import ADMIN, DOCENTE, login
from tests.test_competencies import COHORT, assign, published_tree


def test_publication_and_assignment_are_separate_audited_actions(client, db):
    teacher = login(client, DOCENTE)
    admin = login(client, ADMIN)
    base = db.get(Cohort, COHORT)
    sibling = Cohort(
        id="COH-IA-SIBLING", program_id=base.program_id, call_id=base.call_id,
        nombre="Synthetic parallel cohort", inicio=base.inicio, fin=base.fin,
    )
    db.add(sibling)
    db.commit()

    framework = published_tree(client, teacher, codes=("C1",))
    own_path = f"/api/v1/cohorts/{COHORT}/competencies"
    sibling_path = f"/api/v1/cohorts/{sibling.id}/competencies"
    assert client.get(own_path, headers=teacher).json()["framework"] is None
    assert assign(client, teacher, framework["id"], cohort=sibling.id).status_code == 403
    attached = assign(client, teacher, framework["id"])
    assert attached.status_code == 200, attached.text
    assert attached.json()["framework"]["id"] == framework["id"]
    assert client.get(sibling_path, headers=admin).json()["framework"] is None

    link = db.get(CohortCompetencyFramework, COHORT)
    teacher_id = db.scalar(select(User.id).where(User.email == DOCENTE))
    assert str(link.framework_id) == framework["id"]
    assert link.assigned_by == teacher_id and link.assigned_at is not None
    events = db.scalars(select(AuditEvent).where(AuditEvent.action.in_([
        "competencies.framework_published", "competencies.cohort_framework_assigned",
    ])).order_by(AuditEvent.id)).all()
    assert [(event.action, event.target_id) for event in events] == [
        ("competencies.framework_published", framework["id"]),
        ("competencies.cohort_framework_assigned", COHORT),
    ]
    assert all(event.actor_user_id == teacher_id and event.at is not None for event in events)
