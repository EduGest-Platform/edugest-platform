"""Exercise the prepared HTTP contract using a labelled fixture, not PostgreSQL."""

from datetime import date
from decimal import Decimal
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.deps import current_principal
from app.core.error_handling import install_error_handling
from app.main import app as live_app
from app.modules.learning.attendance_router import attendance_reader, attendance_writer, router
from app.modules.learning.attendance_schemas import AttendanceRecordOut, AttendanceSessionOut
from scripts.export_attendance_candidate import OUT, render
from tests.test_attendance_summary_contract import NOW, SyntheticReader, teacher


def candidate(actor=None, reader=None):
    app = FastAPI()
    install_error_handling(app)
    app.include_router(router, prefix="/api/v1")
    app.dependency_overrides[current_principal] = lambda: actor or teacher()
    if reader is not None:
        app.dependency_overrides[attendance_reader] = lambda: reader
    return app


def url(reader):
    return f"/api/v1/enrollments/{reader.context.enrollment_id}/attendance-summary?date_from=2026-11-16&date_to=2026-11-22"


def test_prepared_route_preserves_unknown_and_fixture_source():
    reader = SyntheticReader()
    with TestClient(candidate(reader=reader)) as client:
        response = client.get(url(reader))
    assert response.status_code == 200
    assert response.json()["source"] == "synthetic_fixture"
    assert response.json()["recorded_absence_days"] is None


def test_user_supplied_cohort_cannot_expand_scope():
    reader = SyntheticReader()
    with TestClient(candidate(actor=teacher(cohort="COH-B"), reader=reader)) as client:
        response = client.get(url(reader) + "&cohort_id=COH-A")
    assert response.status_code == 403
    assert reader.calls == ["context"]


def test_missing_database_adapter_fails_instead_of_returning_demo_data():
    with TestClient(candidate()) as client:
        response = client.get(url(SyntheticReader()))
    assert response.status_code == 503


def test_candidate_declares_bearer_and_matches_exported_contract():
    spec = candidate().openapi()
    path = "/api/v1/enrollments/{enrollment_id}/attendance-summary"
    assert spec["paths"][path]["get"]["security"]
    assert path not in live_app.openapi()["paths"]
    assert OUT.read_text(encoding="utf-8") == render()


def test_write_routes_are_disabled_until_persistence_is_enabled():
    with TestClient(candidate()) as client:
        session = client.post("/api/v1/cohorts/COH-A/attendance-sessions", json={
            "session_date": "2026-11-19", "period": "full_day", "modality": "online",
        })
        record = client.put(f"/api/v1/attendance-sessions/{uuid4()}/records/{uuid4()}", json={
            "status": "full_absence", "justified": False, "correction_reason": "Synthetic correction",
        })
    assert session.status_code == record.status_code == 503


def test_prepared_write_handler_serializes_results_without_internal_reason():
    # HTTP serialization seam only: this fixture does not claim persistence or transaction behavior.
    session_id, enrollment_id = uuid4(), uuid4()

    class FixtureCommands:
        def create_session(self, actor, cohort_id, body):
            return AttendanceSessionOut(id=session_id, cohort_id=cohort_id, session_date=date(2026, 11, 19),
                                        period=body.period, duration_fraction=Decimal("1"), modality=body.modality)

        def save_record(self, actor, session_id, enrollment_id, body):
            return AttendanceRecordOut(id=uuid4(), session_id=session_id, enrollment_id=enrollment_id,
                                       status=body.status, justified=body.justified, absence_days=Decimal("0.5"),
                                       recorded_at=NOW, version=1), True

    app = candidate()
    app.dependency_overrides[attendance_writer] = FixtureCommands
    with TestClient(app) as client:
        session = client.post("/api/v1/cohorts/COH-A/attendance-sessions", json={
            "session_date": "2026-11-19", "period": "full_day", "modality": "online",
        })
        response = client.put(f"/api/v1/attendance-sessions/{session_id}/records/{enrollment_id}", json={
            "status": "morning_absence", "justified": True, "correction_reason": "Private synthetic correction",
        })
    assert session.status_code == response.status_code == 201
    assert Decimal(response.json()["absence_days"]) == Decimal("0.5")
    assert "correction_reason" not in response.json() and "Private synthetic correction" not in response.text


def test_forged_write_fields_are_rejected_before_commands_and_not_echoed():
    class NeverCalled:
        def save_record(self, *args):
            raise AssertionError("Invalid input must not reach write commands")

    app = candidate()
    app.dependency_overrides[attendance_writer] = NeverCalled
    with TestClient(app) as client:
        response = client.put(f"/api/v1/attendance-sessions/{uuid4()}/records/{uuid4()}", json={
            "status": "present", "justified": False, "correction_reason": "Synthetic reason",
            "recorded_by_user_id": "private-synthetic-marker",
        })
    assert response.status_code == 422 and "private-synthetic-marker" not in response.text
