import uuid
from contextlib import contextmanager
from datetime import date, datetime, timezone
from decimal import Decimal
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.core.authz import Principal
from app.core.config import settings
from app.core.db import get_db
from app.core.deps import current_principal
from app.main import app
from app.modules.assistant_tools.schemas import AssignmentStatus, CompetencyDistribution, CompetencyProgress, EnrollmentPending, EnrollmentProgress, LevelCount, PendingSubmissions, StateCount
from app.modules.attendance.models import AttendanceRecord, AttendanceSession
from app.modules.catalog.models import Cohort
from app.modules.identity.models import RoleAssignment
from app.modules.learning import overview_service as service
from app.modules.learning.models import Enrollment

PATH = '/api/v1/cohorts/COH-SYN/progress-overview'
CANARY = 'PRIVATE-OVERVIEW-CANARY'


@pytest.fixture
def overview_http(monkeypatch):
    @contextmanager
    def create(role='coordinacion', size=5, foreign=False):
        monkeypatch.setattr(settings, 'min_group_size', 5)
        cohort = SimpleNamespace(id='COH-SYN', program_id='P-IA', call_id='CALL-SYN', timezone='Europe/Madrid')
        identities = [uuid.uuid4() for _ in range(size)]
        session = SimpleNamespace(id=uuid.uuid4(), session_date=date(2020, 1, 1), duration_fraction=Decimal('0.5'))
        records = [SimpleNamespace(session_id=session.id, enrollment_id=identity, status='presente', modality='presencial', reason=CANARY) for identity in identities]
        now = datetime(2030, 1, 1, tzinfo=timezone.utc)
        suppressed = size < settings.min_group_size
        delivery = PendingSubmissions(timezone=cohort.timezone, suppressed=suppressed, min_group_size=5,
            assignments=[AssignmentStatus(assignment_id=uuid.uuid4(), title='Synthetic activity', due_at=now,
                counts=StateCount(on_time=size, late=0, pending=0, overdue=0, reviewed=0))],
            items=[EnrollmentPending(enrollment_id=identities[0], states={})])
        competency = CompetencyProgress(framework_version=1, suppressed=suppressed, min_group_size=5,
            distribution=[CompetencyDistribution(codigo='C1', nombre='Synthetic competency',
                counts=LevelCount(level_1=size, level_2=0, level_3=0, not_assessed=0))],
            items=[EnrollmentProgress(enrollment_id=identities[0], levels={'C1': 1})])
        metric_calls = []

        def deliveries(*args, **kwargs):
            metric_calls.append('deliveries')
            assert kwargs['per_person'] is False
            return delivery, True

        def competencies(*args, **kwargs):
            metric_calls.append('competencies')
            assert kwargs['per_person'] is False
            return competency, True

        class DatabaseDouble:
            commits = 0

            def __init__(self):
                self.queries, self.events = [], []

            def get(self, model, identity):
                assert model is Cohort
                return cohort if identity == cohort.id else None

            def scalars(self, query):
                entity = query.column_descriptions[0]['entity']
                self.queries.append(entity)
                return {AttendanceSession: [session], Enrollment: identities, AttendanceRecord: records}[entity]

            def add(self, event):
                assert event.action == 'learning.progress_overview_viewed'
                self.events.append(event)

            def commit(self):
                self.commits += 1

        db = DatabaseDouble()
        actor = Principal(user=SimpleNamespace(id=uuid.uuid4()), assignments=[RoleAssignment(role=role,
            scope_type='cohort' if role == 'docente' else 'global', scope_id=('COH-OTHER' if foreign else cohort.id) if role == 'docente' else None)])

        def database():
            yield db

        previous = app.dependency_overrides.copy()
        app.dependency_overrides[get_db] = database
        app.dependency_overrides[current_principal] = lambda: actor
        monkeypatch.setattr(service, 'pending_submissions', deliveries)
        monkeypatch.setattr(service, 'competency_progress', competencies)
        try:
            with TestClient(app, raise_server_exceptions=False) as client:
                yield client, db, identities, metric_calls
        finally:
            app.dependency_overrides.clear()
            app.dependency_overrides.update(previous)
    return create


@pytest.mark.parametrize('role', ['admin', 'coordinacion', 'docente'])
def test_all_authorized_roles_receive_aggregates_without_individual_ids(overview_http, role):
    with overview_http(role) as (client, db, identities, calls):
        response = client.get(PATH)
        assert response.status_code == 200 and response.json()['aggregate_only'] is True
        assert response.json()['attendance']['totals']['attendance_rate'] == 1
        assert CANARY not in response.text and all(str(identity) not in response.text for identity in identities)
        assert 'enrollment_id' not in response.text and 'items' not in response.json()['submissions']
        assert db.commits == 1 and len(db.events) == 1 and calls == ['deliveries', 'competencies']


def test_small_group_hides_counts_and_presence_across_all_sections(overview_http):
    with overview_http(size=4) as (client, db, identities, calls):
        body = client.get(PATH).json()
        assert body['attendance']['totals']['enrollments'] is None
        assert body['attendance']['totals']['attendance_rate'] is None
        for section in ('attendance', 'submissions', 'competencies'):
            assert body[section]['has_data'] is None
        assert all(item['counts'] is None for item in body['submissions']['assignments'])
        assert all(item['counts'] is None for item in body['competencies']['distribution'])


@pytest.mark.parametrize('role,foreign', [('captacion', False), ('docente', True)])
def test_unauthorized_scope_does_not_query_metrics_or_commit_audit(overview_http, role, foreign):
    with overview_http(role=role, foreign=foreign) as (client, db, identities, calls):
        assert client.get(PATH).status_code == 403
        assert db.queries == calls == db.events == [] and db.commits == 0


def test_reversed_period_fails_before_metric_queries(overview_http):
    with overview_http() as (client, db, identities, calls):
        response = client.get(PATH + '?attendance_from=2030-02-01&attendance_to=2030-01-01')
        assert response.status_code == 422 and response.json()['code'] == 'invalid_date_window'
        assert db.queries == calls == db.events == [] and db.commits == 0


@pytest.mark.parametrize('query', ['pending_submissions', 'competency_progress'])
def test_failed_composition_never_commits_a_success_audit_or_leaks_diagnostics(overview_http, monkeypatch, query):
    with overview_http() as (client, db, identities, calls):
        def fail(*args, **kwargs):
            raise RuntimeError(CANARY)
        monkeypatch.setattr(service, query, fail)
        response = client.get(PATH)
        assert response.status_code == 500 and CANARY not in response.text
        assert db.commits == 0 and db.events == []
