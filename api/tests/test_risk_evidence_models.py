"""KAN-171: PostgreSQL constraints preserve synthetic evidence and human support records."""
from datetime import date

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.modules.identity.models import User
from app.modules.learning.models import Enrollment
from app.modules.risk.models import Intervention, RiskAlert


def evidence(db, **changes):
    values = dict(enrollment_id=db.scalar(select(Enrollment.id)), model_version="synthetic-baseline-v1",
                  model_hash="a" * 64, cutoff=date(2026, 11, 24), status="abstained", abstention_reason="insufficient_exposure")
    return RiskAlert(**{**values, **changes})


def test_abstention_persists_without_inventing_a_zero_score(db):
    row = evidence(db)
    db.add(row)
    db.commit()
    assert row.synthetic_proxy_score is None and row.experimental_support_signal is None
    assert row.synthetic_only and row.human_review_only and not row.validated_for_people
    assert row.review_state == "pending"


@pytest.mark.parametrize("changes", [
    {"status": "scored", "abstention_reason": None},
    {"synthetic_only": False}, {"human_review_only": False}, {"validated_for_people": True},
    {"attendance_unknown_fraction": 1.1}, {"unjustified_absence_days": -1},
    {"mean_competency_level": 4}, {"review_state": "expelled"},
])
def test_invalid_or_real_world_evidence_is_rejected(db, changes):
    db.add(evidence(db, **changes))
    with pytest.raises(IntegrityError):
        db.flush()
    db.rollback()


def test_same_observation_cannot_be_persisted_twice(db):
    db.add(evidence(db))
    db.commit()
    db.add(evidence(db))
    with pytest.raises(IntegrityError):
        db.flush()
    db.rollback()


def test_intervention_requires_a_human_actor_and_preserves_learning_state(db):
    row = evidence(db)
    db.add(row)
    db.flush()
    enrollment = db.get(Enrollment, row.enrollment_id)
    initial = enrollment.estado
    db.add(Intervention(alert_id=row.id, actor_user_id=db.scalar(select(User.id)), kind="support", note="Synthetic study support"))
    db.commit()
    db.refresh(enrollment)
    assert enrollment.estado == initial


def test_automatic_punitive_action_is_not_an_intervention_kind(db):
    row = evidence(db)
    db.add(row)
    db.flush()
    db.add(Intervention(alert_id=row.id, actor_user_id=db.scalar(select(User.id)), kind="expel", note="Synthetic invalid action"))
    with pytest.raises(IntegrityError):
        db.flush()
    db.rollback()
