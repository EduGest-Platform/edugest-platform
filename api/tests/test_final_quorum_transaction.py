"""KAN-163: pending signatures must survive a failed final transaction without partial admission."""
from sqlalchemy import func, select

from app.core import audit
from app.modules.admissions.models import Application, ApplicationEvent
from app.modules.audit.models import AuditEvent
from app.modules.catalog.models import Call
from app.modules.learning.models import Enrollment
from app.modules.selection.models import SelectionApproval, SelectionDecision
from tests.conftest import ADMIN, COORD, SEL_IA, login
from tests.test_selection_decisions import IA_CALL, decide, make_application, make_cohort


def state(db, target):
    db.expire_all()
    return {
        'stage': db.get(Application, target.id).stage,
        'votes': list(db.scalars(select(SelectionApproval.id).where(SelectionApproval.application_id == target.id).order_by(SelectionApproval.id))),
        'closed': db.scalar(select(func.count()).select_from(SelectionApproval).where(SelectionApproval.application_id == target.id, SelectionApproval.decision_id.is_not(None))),
        'decisions': db.scalar(select(func.count()).select_from(SelectionDecision).where(SelectionDecision.application_id == target.id)),
        'enrollments': db.scalar(select(func.count()).select_from(Enrollment).where(Enrollment.application_id == target.id)),
        'events': db.scalar(select(func.count()).select_from(ApplicationEvent).where(ApplicationEvent.application_id == target.id)),
        'audit': db.scalar(select(func.count()).select_from(AuditEvent).where(AuditEvent.target_id == str(target.id))),
    }


def setup(db):
    make_cohort(db)
    db.get(Call, IA_CALL).selection_quorum = 2
    db.commit()
    return make_application(db, stage='evaluacion_en_curso')


def test_failed_final_signature_rolls_back_only_its_transaction_and_retry_can_succeed(client, db, monkeypatch):
    target = setup(db)
    first, second = login(client, SEL_IA), login(client, COORD)
    assert decide(client, first, target.id).status_code == 202
    before = state(db, target)
    assert len(before['votes']) == 1 and before['enrollments'] == before['decisions'] == 0
    original = audit.record

    def fail_final_audit(db, actor, action, target_type, target_id, **meta):
        if action == 'selection.decided':
            raise RuntimeError('Synthetic final audit failure')
        return original(db, actor, action, target_type, target_id, **meta)

    with monkeypatch.context() as patch:
        patch.setattr(audit, 'record', fail_final_audit)
        assert decide(client, second, target.id).status_code == 500
    assert state(db, target) == before
    assert decide(client, second, target.id).status_code == 201
    after = state(db, target)
    assert after['stage'] == 'admitida'
    assert len(after['votes']) == after['closed'] == 2
    assert after['decisions'] == after['enrollments'] == 1


def test_another_admission_can_consume_the_last_place_between_two_signatures(client, db):
    target = setup(db)
    rival = make_application(db)
    admitted = db.scalar(select(func.count()).select_from(Application).where(Application.call_id == IA_CALL, Application.stage == 'admitida'))
    db.get(Call, IA_CALL).plazas = admitted + 1
    db.commit()
    selector, coordinator, admin = login(client, SEL_IA), login(client, COORD), login(client, ADMIN)
    assert decide(client, selector, target.id).status_code == 202
    assert decide(client, selector, rival.id).status_code == 202
    assert decide(client, coordinator, rival.id).status_code == 201
    before = state(db, target)
    denied = decide(client, admin, target.id)
    assert denied.status_code == 409 and denied.json()['code'] == 'no_places_left'
    assert state(db, target) == before
    assert before['enrollments'] == before['decisions'] == before['closed'] == 0
