"""Negative and positive authorisation tests: role + scope enforced by the API, not by the UI."""

from collections import Counter

from sqlalchemy import func, select

from app.core.config import settings
from app.modules.admissions.models import Application
from app.modules.catalog.models import Call
from tests.conftest import ADMIN, ASPIRANTE, CAPT_DATA, CAPT_IA, CODER, COORD, DOCENTE, SEL_IA, login


def apps(client, h, **params):
    return client.get("/api/v1/applications", headers=h, params=params)


def an_app(client, program):
    items = apps(client, login(client, ADMIN), limit=200).json()["items"]
    return next(a for a in items if a["program_id"] == program)


def all_applications(db):
    return db.scalar(select(func.count()).select_from(Application))


def in_program(db, program):
    """Expected scope read from the seeded data, so the test checks the rule and not a fixed number."""
    return db.scalar(select(func.count()).select_from(Application).join(Call, Call.id == Application.call_id)
                     .where(Call.program_id == program))


def stages_in_call(db, call):
    rows = db.execute(select(Application.stage, func.count()).where(Application.call_id == call).group_by(Application.stage))
    return Counter(dict(rows.all()))


def test_unauthenticated_cannot_list(client):
    assert client.get("/api/v1/applications").status_code == 401


def test_admin_sees_every_call(client, db):
    r = apps(client, login(client, ADMIN))
    assert r.status_code == 200 and r.json()["total"] == all_applications(db)


def test_captacion_is_limited_to_its_program(client, db):
    h = login(client, CAPT_IA)
    body = apps(client, h).json()
    assert body["total"] == in_program(db, "P-IA") and {a["program_id"] for a in body["items"]} == {"P-IA"}
    assert 0 < body["total"] < all_applications(db)
    data_app = an_app(client, "P-DATA")
    assert client.get(f"/api/v1/applications/{data_app['id']}", headers=h).status_code == 403
    r = client.post(f"/api/v1/applications/{data_app['id']}/events", headers=h, json={"tipo": "nota", "resumen": "x"})
    assert r.status_code == 403
    # filtering by a foreign call returns nothing instead of leaking
    assert apps(client, h, call_id="CONV-DATA-2027A").json()["total"] == 0
    assert apps(client, login(client, CAPT_DATA)).json()["total"] == in_program(db, "P-DATA")


def test_seleccion_is_limited_to_its_call(client, db):
    h = login(client, SEL_IA)
    body = apps(client, h).json()
    expected = sum(stages_in_call(db, "CONV-IA-2027A").values())
    assert body["total"] == expected and {a["call_id"] for a in body["items"]} == {"CONV-IA-2027A"}
    assert 0 < body["total"] < all_applications(db)
    assert client.get(f"/api/v1/applications/{an_app(client, 'P-DATA')['id']}", headers=h).status_code == 403


def test_docente_has_no_access_to_admissions(client):
    h = login(client, DOCENTE)
    assert apps(client, h).status_code == 403
    assert client.get(f"/api/v1/applications/{an_app(client, 'P-IA')['id']}", headers=h).status_code == 403
    assert client.get("/api/v1/calls/CONV-IA-2027A/summary", headers=h).status_code == 403


def test_coordinacion_gets_only_suppressed_aggregates(client, db):
    h = login(client, COORD)
    assert apps(client, h).status_code == 403
    r = client.get("/api/v1/calls/CONV-IA-2027A/summary", headers=h)
    assert r.status_code == 200
    s = r.json()
    real = stages_in_call(db, "CONV-IA-2027A")
    assert s["total"] == sum(real.values()) and not s["suppressed"]
    # a stage below min_cell_size is hidden; any other stage shows its real count
    for cell in s["by_stage"]:
        n = real[cell["stage"]]
        hidden = 0 < n < settings.min_cell_size
        assert cell["suppressed"] == hidden and cell["count"] == (None if hidden else n), cell
    assert "person" not in r.text and "@" not in r.text


def test_small_groups_are_fully_suppressed(client):
    h = login(client, COORD)
    s = client.get("/api/v1/calls/CONV-IA-2026B/summary", headers=h).json()
    assert s["total"] is None and s["suppressed"]


def test_person_accounts_cannot_use_staff_endpoints(client):
    for who in (ASPIRANTE, CODER):
        h = login(client, who)
        assert apps(client, h).status_code == 403
        assert client.get(f"/api/v1/applications/{an_app(client, 'P-IA')['id']}", headers=h).status_code == 403
        assert client.get("/api/v1/audit-events", headers=h).status_code == 403
    assert client.get("/api/v1/me/applications", headers=login(client, CODER)).json() == []


def test_audit_is_admin_only(client):
    assert client.get("/api/v1/audit-events", headers=login(client, CAPT_IA)).status_code == 403
    assert client.get("/api/v1/audit-events", headers=login(client, ADMIN)).status_code == 200


def test_coder_and_aspirant_states_come_from_the_same_person(client):
    me = client.get("/api/v1/auth/me", headers=login(client, CODER)).json()
    assert me["roles"] == [] and me["enrollments"] == [{"cohort_id": "COH-IA", "estado": "activa"}]
