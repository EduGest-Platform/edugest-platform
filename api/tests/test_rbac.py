"""Negative and positive authorisation tests: role + scope enforced by the API, not by the UI."""

from tests.conftest import ADMIN, ASPIRANTE, CAPT_DATA, CAPT_IA, CODER, COORD, DOCENTE, SEL_IA, login


def apps(client, h, **params):
    return client.get("/api/v1/applications", headers=h, params=params)


def an_app(client, program):
    items = apps(client, login(client, ADMIN), limit=200).json()["items"]
    return next(a for a in items if a["program_id"] == program)


def test_unauthenticated_cannot_list(client):
    assert client.get("/api/v1/applications").status_code == 401


def test_admin_sees_every_call(client):
    r = apps(client, login(client, ADMIN))
    assert r.status_code == 200 and r.json()["total"] == 12


def test_captacion_is_limited_to_its_program(client):
    h = login(client, CAPT_IA)
    body = apps(client, h).json()
    assert body["total"] == 6 and {a["program_id"] for a in body["items"]} == {"P-IA"}
    data_app = an_app(client, "P-DATA")
    assert client.get(f"/api/v1/applications/{data_app['id']}", headers=h).status_code == 403
    r = client.post(f"/api/v1/applications/{data_app['id']}/events", headers=h, json={"tipo": "nota", "resumen": "x"})
    assert r.status_code == 403
    # filtering by a foreign call returns nothing instead of leaking
    assert apps(client, h, call_id="CONV-DATA-2027A").json()["total"] == 0
    assert apps(client, login(client, CAPT_DATA)).json()["total"] == 6


def test_seleccion_is_limited_to_its_call(client):
    h = login(client, SEL_IA)
    body = apps(client, h).json()
    assert body["total"] == 6 and {a["call_id"] for a in body["items"]} == {"CONV-IA-2027A"}
    assert client.get(f"/api/v1/applications/{an_app(client, 'P-DATA')['id']}", headers=h).status_code == 403


def test_docente_has_no_access_to_admissions(client):
    h = login(client, DOCENTE)
    assert apps(client, h).status_code == 403
    assert client.get(f"/api/v1/applications/{an_app(client, 'P-IA')['id']}", headers=h).status_code == 403
    assert client.get("/api/v1/calls/CONV-IA-2027A/summary", headers=h).status_code == 403


def test_coordinacion_gets_only_suppressed_aggregates(client):
    h = login(client, COORD)
    assert apps(client, h).status_code == 403
    r = client.get("/api/v1/calls/CONV-IA-2027A/summary", headers=h)
    assert r.status_code == 200
    s = r.json()
    assert s["total"] == 6 and not s["suppressed"]
    # 6 applications spread over stages -> every non-empty cell is < 3 and must be hidden
    assert all(c["count"] in (0, None) for c in s["by_stage"])
    assert any(c["suppressed"] for c in s["by_stage"])
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
