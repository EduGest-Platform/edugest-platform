import pytest
from sqlalchemy import func, select

from app.core.config import settings
from app.modules.audit.models import AuditEvent
from app.modules.identity.models import Person, RoleAssignment, User
from app.modules.submissions.models import Submission
from app.seed import load_seed
from app.seed_academic import load_academic
from tests.conftest import CAPT_IA, CODER, COORD, DOCENTE, login

PATH = '/api/v1/cohorts/COH-IA/progress-overview'


@pytest.fixture
def academic(db):
    load_academic(db, load_seed())


def test_overview_matches_existing_attendance_aggregate_for_authorized_roles(client, academic):
    for account in (COORD, DOCENTE):
        headers = login(client, account)
        response = client.get(PATH, headers=headers)
        assert response.status_code == 200
        previous = client.get('/api/v1/cohorts/COH-IA/attendance-summary', headers=headers)
        assert response.json()['attendance']['totals'] == previous.json()['cohort_totals']
        assert response.json()['aggregate_only'] is True
        assert response.headers['cache-control'] == 'no-store'


def test_unauthorized_role_is_denied_before_reversed_period_validation(client, academic):
    query = '?attendance_from=2030-02-01&attendance_to=2030-01-01'
    assert client.get(PATH + query, headers=login(client, CAPT_IA)).status_code == 403
    response = client.get(PATH + query, headers=login(client, COORD))
    assert response.status_code == 422 and response.json()['code'] == 'invalid_date_window'


def test_overview_submission_counts_match_the_existing_aggregate_tool(client, academic):
    headers = login(client, COORD)
    overview = client.get(PATH, headers=headers)
    previous = client.get('/api/v1/tools/pending-submissions?cohort_id=COH-IA', headers=headers)
    assert overview.status_code == previous.status_code == 200
    assert overview.json()['submissions']['assignments'] == previous.json()['data']['assignments']
    assert 'items' not in overview.json()['submissions']


def test_overview_competencies_match_the_existing_aggregate_tool(client, academic):
    headers = login(client, COORD)
    overview = client.get(PATH, headers=headers)
    previous = client.get('/api/v1/tools/competency-progress?cohort_id=COH-IA', headers=headers)
    assert overview.status_code == previous.status_code == 200
    assert overview.json()['competencies']['distribution'] == previous.json()['data']['distribution']
    assert overview.json()['competencies']['framework_version'] == previous.json()['data']['framework_version']
    assert 'items' not in overview.json()['competencies']


def test_small_groups_are_suppressed_even_for_teachers(client, academic, monkeypatch):
    monkeypatch.setattr(settings, 'min_group_size', 100000)
    response = client.get(PATH, headers=login(client, DOCENTE))
    assert response.status_code == 200
    body = response.json()
    assert body['attendance']['totals']['enrollments'] is None
    for section in ('attendance', 'submissions', 'competencies'):
        assert body[section]['has_data'] is None
    assert body['submissions']['assignments'] and body['competencies']['distribution']
    assert all(item['counts'] is None for item in body['submissions']['assignments'])
    assert all(item['counts'] is None for item in body['competencies']['distribution'])


def test_overview_excludes_person_names_and_existing_submission_urls(client, academic, db):
    canary = 'PRIVATE-OVERVIEW-PERSON'
    db.query(Person).update({Person.display_name: canary})
    db.commit()
    urls = list(db.scalars(select(Submission.portfolio_url)))
    assert urls
    response = client.get(PATH, headers=login(client, COORD))
    assert response.status_code == 200 and canary not in response.text
    assert all(url not in response.text for url in urls)
    assert 'portfolio_url' not in response.text and 'enrollment_id' not in response.text


def test_foreign_teacher_and_coder_cannot_use_the_overview(client, academic, db):
    teacher_id = db.scalar(select(User.id).where(User.email == DOCENTE))
    db.query(RoleAssignment).filter(RoleAssignment.user_id == teacher_id, RoleAssignment.scope_id == 'COH-IA').delete()
    db.commit()
    assert client.get(PATH, headers=login(client, DOCENTE)).status_code == 403
    assert client.get(PATH, headers=login(client, CODER)).status_code == 403


def test_overview_writes_exactly_one_completion_audit(client, academic, db):
    before = db.scalar(select(func.count()).select_from(AuditEvent).where(AuditEvent.action == 'learning.progress_overview_viewed'))
    assert client.get(PATH, headers=login(client, COORD)).status_code == 200
    assert db.scalar(select(func.count()).select_from(AuditEvent).where(AuditEvent.action == 'learning.progress_overview_viewed')) == before + 1
