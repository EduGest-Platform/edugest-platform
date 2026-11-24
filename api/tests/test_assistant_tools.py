"""KAN-263: read-only assistant tools. Envelope, cohort scope, aggregate-only coordination, abstention and privacy."""

from datetime import timedelta

import pytest
from sqlalchemy import select

from app.core.db import utcnow
from app.modules.identity.models import RoleAssignment, User
from app.seed import load_seed
from app.seed_academic import load_academic
from tests.conftest import ADMIN, CAPT_IA, CODER, COORD, DOCENTE, login

COHORT, OTHER = "COH-IA", "COH-DATA"
ENVELOPE = {"tool", "scope", "period", "generated_at", "source", "rule", "aggregate_only", "has_data", "data"}
TOOLS = ["attendance-summary", "competency-progress", "pending-submissions"]


@pytest.fixture
def academic(db):
    load_academic(db, load_seed())


@pytest.fixture
def teacher(client):
    return login(client, DOCENTE)


def call(client, headers, tool, cohort_id=COHORT):
    return client.get(f"/api/v1/tools/{tool}", params={"cohort_id": cohort_id}, headers=headers)


@pytest.mark.parametrize("tool", TOOLS)
def test_every_tool_answers_with_the_common_envelope(client, academic, teacher, tool):
    r = call(client, teacher, tool)
    assert r.status_code == 200, r.text
    body = r.json()
    assert set(body) == ENVELOPE
    assert body["scope"]["cohort_id"] == COHORT and body["rule"] and body["source"]
    assert body["aggregate_only"] is False and body["has_data"] is True


@pytest.mark.parametrize("tool", TOOLS)
def test_teacher_of_another_cohort_gets_403(client, db, academic, tool):
    teacher_id = db.scalar(select(User.id).where(User.email == DOCENTE))
    db.query(RoleAssignment).filter(RoleAssignment.user_id == teacher_id, RoleAssignment.scope_id == COHORT).delete()
    db.commit()
    headers = login(client, DOCENTE)  # now only teaches COH-DATA
    assert call(client, headers, tool).status_code == 403
    assert call(client, headers, tool, OTHER).status_code == 200


@pytest.mark.parametrize("account", [CODER, CAPT_IA])
@pytest.mark.parametrize("tool", TOOLS)
def test_non_staff_and_admissions_staff_cannot_use_academic_tools(client, academic, account, tool):
    assert call(client, login(client, account), tool).status_code == 403


@pytest.mark.parametrize("tool", TOOLS)
def test_coordination_gets_totals_without_any_enrollment(client, academic, tool):
    r = call(client, login(client, COORD), tool)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["aggregate_only"] is True
    assert body["data"]["items"] == []
    assert "enrollment_id" not in str(body["data"])


def test_pending_submissions_counts_match_the_seed_cases(client, academic, teacher):
    data = call(client, teacher, "pending-submissions").json()["data"]
    counts = data["assignments"][0]["counts"]
    enrollments = len(data["items"])
    assert sum(counts[k] for k in ("on_time", "late", "pending", "overdue")) == enrollments
    assert counts["late"] >= 1 and counts["overdue"] >= 1


def test_competency_progress_never_reports_zero(client, academic, teacher):
    data = call(client, teacher, "competency-progress").json()["data"]
    levels = [lvl for item in data["items"] for lvl in item["levels"].values()]
    assert levels and all(lvl in (1, 2, 3, None) for lvl in levels)


def test_cohort_without_data_abstains_instead_of_reporting_zeros(client, teacher):
    # Without the academic seed there are no frameworks, assignments or attendance sessions.
    for tool in TOOLS:
        body = call(client, teacher, tool).json()
        assert body["has_data"] is False, tool


def test_small_groups_are_suppressed_for_coordination(client, db, academic, monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "min_group_size", 100)
    body = call(client, login(client, COORD), "pending-submissions").json()["data"]
    assert body["suppressed"] is True and all(a["counts"] is None for a in body["assignments"])


def test_submission_context_has_rubric_and_checks_but_no_url(client, db, academic, teacher):
    pending = call(client, teacher, "pending-submissions").json()["data"]
    assignment_id = pending["assignments"][0]["assignment_id"]
    from app.modules.submissions.models import Submission

    submission = db.scalar(select(Submission).where(Submission.assignment_id == assignment_id))
    r = client.get(f"/api/v1/tools/submissions/{submission.id}", headers=teacher)
    assert r.status_code == 200, r.text
    context = r.json()["data"]
    assert context["rubric"] and context["check_results"]["total"] == 10
    assert "example.test" not in r.text and "portfolio" not in r.text
    assert client.get(f"/api/v1/tools/submissions/{submission.id}", headers=login(client, COORD)).status_code == 403


def test_unknown_cohort_is_404(client, teacher):
    assert call(client, teacher, "pending-submissions", "COH-NOPE").status_code == 404


def test_admin_has_global_scope(client, academic):
    assert call(client, login(client, ADMIN), "pending-submissions", OTHER).status_code == 200


def test_period_of_pending_submissions_ends_today(client, academic, teacher):
    period = call(client, teacher, "pending-submissions").json()["period"]
    assert period["date_to"] in {(utcnow() - timedelta(days=1)).date().isoformat(), utcnow().date().isoformat()}


# ---------- KAN-158: only active enrollments ----------


def _first_enrollment_of(db, cohort_id):
    from app.modules.learning.models import Enrollment

    query = select(Enrollment).where(Enrollment.cohort_id == cohort_id).order_by(Enrollment.created_at, Enrollment.id)
    return db.scalars(query).first()


@pytest.mark.parametrize("estado,left_out", [("baja_voluntaria", True), ("finalizada", False)])
@pytest.mark.parametrize("tool", TOOLS)
def test_withdrawn_enrollments_are_left_out_but_finished_ones_stay(client, db, academic, teacher, tool, estado, left_out):
    before = call(client, teacher, tool).json()["data"]["items"]
    enrollment = _first_enrollment_of(db, COHORT)
    gone = str(enrollment.id)
    enrollment.estado = estado
    db.commit()
    after = call(client, teacher, tool).json()["data"]["items"]
    assert len(after) == (len(before) - 1 if left_out else len(before))
    assert (gone in {item["enrollment_id"] for item in after}) is not left_out


def test_coder_who_left_is_neither_overdue_nor_counted_in_totals(client, db, academic, teacher):
    from sqlalchemy import func

    from app.modules.learning.models import Enrollment

    enrollment = _first_enrollment_of(db, COHORT)
    gone = str(enrollment.id)
    enrollment.estado = "baja_voluntaria"
    db.commit()
    counted = db.scalar(select(func.count()).select_from(Enrollment).where(Enrollment.cohort_id == COHORT, Enrollment.estado != "baja_voluntaria"))
    data = call(client, teacher, "pending-submissions").json()["data"]
    assert data["assignments"]
    for assignment in data["assignments"]:
        counts = assignment["counts"]
        assert sum(counts[k] for k in ("on_time", "late", "pending", "overdue")) == counted
    assert gone not in str(data)
