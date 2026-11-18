"""Executable version of docs/reports/RBAC_MATRIX_2026-11-18.md: one status per profile and endpoint."""

import pytest

from tests.conftest import ADMIN, ASPIRANTE, CAPT_IA, CODER, COORD, DOCENTE, SEL_IA, login

OWN_PROGRAM, OTHER_PROGRAM = "P-IA", "P-DATA"
OWN_CALL, OTHER_CALL = "CONV-IA-2027A", "CONV-DATA-2027A"
NO_ACCESS = dict(list=403, detail_own=403, event_own=403, detail_other=403, summary_own=403, summary_other=403, audit=403)
SCOPED_STAFF = dict(list=200, detail_own=200, event_own=201, detail_other=403, summary_own=200, summary_other=403, audit=403)
LOGGED_IN = dict(mine=200, me=200)

# profile -> (account or None, expected status per endpoint). Staff accounts hold the program/call of the seed.
MATRIX = {
    "anonymous": (None, {key: 401 for key in [*NO_ACCESS, *LOGGED_IN]}),
    "aspirante": (ASPIRANTE, {**NO_ACCESS, **LOGGED_IN}),
    "coder": (CODER, {**NO_ACCESS, **LOGGED_IN}),
    "captacion": (CAPT_IA, {**SCOPED_STAFF, **LOGGED_IN}),
    "seleccion": (SEL_IA, {**SCOPED_STAFF, **LOGGED_IN}),
    "coordinacion": (COORD, {**NO_ACCESS, "summary_own": 200, "summary_other": 200, **LOGGED_IN}),
    "docente": (DOCENTE, {**NO_ACCESS, **LOGGED_IN}),
    "admin": (ADMIN, {**SCOPED_STAFF, "detail_other": 200, "summary_other": 200, "audit": 200, **LOGGED_IN}),
}
STAFF = {"captacion", "seleccion", "coordinacion", "docente", "admin"}


def call_endpoint(client, key, headers, app_ids):
    match key:
        case "list":
            return client.get("/api/v1/applications", headers=headers)
        case "detail_own":
            return client.get(f"/api/v1/applications/{app_ids[OWN_PROGRAM]}", headers=headers)
        case "detail_other":
            return client.get(f"/api/v1/applications/{app_ids[OTHER_PROGRAM]}", headers=headers)
        case "event_own":
            return client.post(f"/api/v1/applications/{app_ids[OWN_PROGRAM]}/events", headers=headers, json={"tipo": "nota", "resumen": "matrix check"})
        case "summary_own":
            return client.get(f"/api/v1/calls/{OWN_CALL}/summary", headers=headers)
        case "summary_other":
            return client.get(f"/api/v1/calls/{OTHER_CALL}/summary", headers=headers)
        case "audit":
            return client.get("/api/v1/audit-events", headers=headers)
        case "mine":
            return client.get("/api/v1/me/applications", headers=headers)
        case "me":
            return client.get("/api/v1/auth/me", headers=headers)


@pytest.mark.parametrize("profile", MATRIX)
def test_endpoint_statuses_match_the_documented_matrix(client, profile):
    account, expected = MATRIX[profile]
    items = client.get("/api/v1/applications", headers=login(client, ADMIN), params={"limit": 200}).json()["items"]
    app_ids = {program: next(a["id"] for a in items if a["program_id"] == program) for program in (OWN_PROGRAM, OTHER_PROGRAM)}
    headers = login(client, account) if account else {}
    actual = {key: call_endpoint(client, key, headers, app_ids).status_code for key in expected}
    assert actual == expected
    if profile in STAFF:  # staff accounts are not linked to a person, so they own no applications
        assert client.get("/api/v1/me/applications", headers=headers).json() == []


def test_public_routes_need_no_session(client):
    assert client.get("/health").status_code == 200
    assert client.get("/api/v1/calls").status_code == 200
