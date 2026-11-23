"""KAN-151: the assistant's document scope is decided on the server, per role and per active enrollment."""

import pytest
from sqlalchemy import select, update

from app.core.authz import Principal
from app.modules.catalog.models import Cohort
from app.modules.identity.models import RoleAssignment, User
from app.modules.knowledge.scope import knowledge_scope
from app.modules.learning.models import Enrollment
from tests.conftest import ADMIN, ASPIRANTE, CAPT_IA, CODER, COORD, DOCENTE, SEL_IA


def principal(db, email: str) -> Principal:
    user = db.scalar(select(User).where(User.email == email))
    rows = db.scalars(select(RoleAssignment).where(RoleAssignment.user_id == user.id, RoleAssignment.revoked_at.is_(None)))
    return Principal(user=user, assignments=list(rows))


@pytest.mark.parametrize("email", [ADMIN, COORD])
def test_admin_and_coordination_read_every_cohort(db, email):
    every = set(db.scalars(select(Cohort.id)))
    scope = knowledge_scope(db, principal(db, email))
    assert scope.cohorts == every and not scope.is_empty


def test_teacher_reads_only_its_own_cohorts(db):
    assert knowledge_scope(db, principal(db, DOCENTE)).cohorts == {"COH-IA", "COH-DATA"}


def test_coder_reads_only_the_cohort_of_its_active_enrollment(db):
    scope = knowledge_scope(db, principal(db, CODER))
    assert scope.cohorts == {"COH-IA"} and scope.programs == {"P-IA"}


def test_coder_who_left_reads_nothing(db):
    coder = principal(db, CODER)
    db.execute(update(Enrollment).where(Enrollment.person_id == coder.user.person_id).values(estado="baja_voluntaria"))
    db.commit()
    assert knowledge_scope(db, coder).is_empty


@pytest.mark.parametrize("email", [CAPT_IA, SEL_IA, ASPIRANTE])
def test_admissions_staff_and_applicants_read_nothing(db, email):
    assert knowledge_scope(db, principal(db, email)).is_empty
