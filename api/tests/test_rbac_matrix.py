"""Executable version of docs/reports/RBAC_MATRIX_2026-11-18.md: one status per profile and endpoint.

Section 3 of the report says which cells this file asserts and which ones are covered by other suites.
"""

import itertools

import pytest
from sqlalchemy import select

from app.core.config import settings
from app.modules.admissions.models import Application
from app.modules.identity.models import User
from tests.conftest import ADMIN, ASPIRANTE, CAPT_IA, CODER, COORD, DOCENTE, SEL_IA, login, new_application

OWN_PROGRAM, OTHER_PROGRAM = "P-IA", "P-DATA"
OWN_CALL, OTHER_CALL = "CONV-IA-2027A", "CONV-DATA-2027A"
UNKNOWN_ACCOUNT = "nadie.registrado@example.test"
email_counter = itertools.count(1)

NO_ACCESS = dict(
    list=403, detail_own=403, detail_other=403, event_own=403, event_other=403, summary_own=403, summary_other=403, audit=403,
)
# Out-of-scope applications answer 404, like an unknown id (PO decision 19/11/2026); summaries keep 403 (call ids are public).
SCOPED_STAFF = dict(
    list=200, detail_own=200, detail_other=404, event_own=201, event_other=404, summary_own=200, summary_other=403, audit=403,
)
LOGGED_IN = dict(mine=200, me=200)
# Public routes: the credentials sent decide login; a bearer is optional for the public inscription form.
PUBLIC = dict(login=200, create_application=201)

# profile -> (account or None, expected status per endpoint). Staff accounts hold the program/call of the seed.
MATRIX = {
    "anonymous": (None, {**{key: 401 for key in [*NO_ACCESS, *LOGGED_IN]}, "login": 401, "create_application": 201}),
    "aspirante": (ASPIRANTE, {**NO_ACCESS, **LOGGED_IN, **PUBLIC}),
    "coder": (CODER, {**NO_ACCESS, **LOGGED_IN, **PUBLIC}),
    "captacion": (CAPT_IA, {**SCOPED_STAFF, **LOGGED_IN, **PUBLIC}),
    "seleccion": (SEL_IA, {**SCOPED_STAFF, **LOGGED_IN, **PUBLIC}),
    "coordinacion": (COORD, {**NO_ACCESS, "summary_own": 200, "summary_other": 200, **LOGGED_IN, **PUBLIC}),
    "docente": (DOCENTE, {**NO_ACCESS, **LOGGED_IN, **PUBLIC}),
    "admin": (ADMIN, {**SCOPED_STAFF, "detail_other": 200, "event_other": 201, "summary_other": 200, "audit": 200, **LOGGED_IN, **PUBLIC}),
}
STAFF = {"captacion", "seleccion", "coordinacion", "docente", "admin"}

# What a list may contain for each profile that can list: (field, allowed values). None means every program.
LIST_SCOPE = {"captacion": ("program_id", {OWN_PROGRAM}), "seleccion": ("call_id", {OWN_CALL}), "admin": None}


def login_attempt(client, account):
    """POST /auth/login needs no session: real credentials get 200, an unknown account gets the generic 401."""
    if account is None:
        return client.post("/api/v1/auth/login", json={"email": UNKNOWN_ACCOUNT, "password": "synthetic-wrong-password"})
    return client.post("/api/v1/auth/login", json={"email": account, "password": settings.demo_password})


def call_endpoint(client, key, headers, app_ids, account):
    match key:
        case "login":
            return login_attempt(client, account)
        case "create_application":
            body = new_application(email=f"rbac.matrix.{next(email_counter)}@example.test")
            return client.post("/api/v1/applications", headers=headers, json=body)
        case "list":
            return client.get("/api/v1/applications", headers=headers)
        case "detail_own":
            return client.get(f"/api/v1/applications/{app_ids[OWN_PROGRAM]}", headers=headers)
        case "detail_other":
            return client.get(f"/api/v1/applications/{app_ids[OTHER_PROGRAM]}", headers=headers)
        case "event_own":
            return client.post(f"/api/v1/applications/{app_ids[OWN_PROGRAM]}/events", headers=headers, json={"tipo": "nota", "resumen": "matrix check"})
        case "event_other":
            return client.post(f"/api/v1/applications/{app_ids[OTHER_PROGRAM]}/events", headers=headers, json={"tipo": "nota", "resumen": "matrix check"})
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


def seed_application_ids(client) -> dict[str, str]:
    items = client.get("/api/v1/applications", headers=login(client, ADMIN), params={"limit": 200}).json()["items"]
    return {program: next(a["id"] for a in items if a["program_id"] == program) for program in (OWN_PROGRAM, OTHER_PROGRAM)}


@pytest.mark.parametrize("profile", MATRIX)
def test_endpoint_statuses_match_the_documented_matrix(client, profile):
    account, expected = MATRIX[profile]
    app_ids = seed_application_ids(client)
    headers = login(client, account) if account else {}
    actual = {key: call_endpoint(client, key, headers, app_ids, account).status_code for key in expected}
    assert actual == expected
    if profile in STAFF:  # staff accounts are not linked to a person, so they own no applications
        assert client.get("/api/v1/me/applications", headers=headers).json() == []


@pytest.mark.parametrize("profile", MATRIX)
def test_logout_ends_only_a_valid_session(client, profile):
    account, _ = MATRIX[profile]
    if account is None:
        assert client.post("/api/v1/auth/logout").status_code == 401
        return
    headers = login(client, account)
    assert client.post("/api/v1/auth/logout", headers=headers).status_code == 204
    assert client.get("/api/v1/auth/me", headers=headers).status_code == 401
    assert client.post("/api/v1/auth/logout", headers=headers).status_code == 401


@pytest.mark.parametrize("profile", LIST_SCOPE)
def test_lists_contain_only_applications_inside_the_scope(client, profile):
    """A 200 is not enough: a scoped list must never include applications from another program or call."""
    account, _ = MATRIX[profile]
    app_ids = seed_application_ids(client)
    items = client.get("/api/v1/applications", headers=login(client, account), params={"limit": 200}).json()["items"]
    assert items, "the seed gives every listing profile at least one application"
    returned = {item["id"] for item in items}
    if LIST_SCOPE[profile] is None:
        assert {OWN_PROGRAM, OTHER_PROGRAM} <= {item["program_id"] for item in items}
        assert set(app_ids.values()) <= returned
        return
    field, allowed = LIST_SCOPE[profile]
    assert {item[field] for item in items} == allowed
    assert app_ids[OTHER_PROGRAM] not in returned and app_ids[OWN_PROGRAM] in returned


@pytest.mark.parametrize("profile", ["captacion", "seleccion"])
def test_query_parameters_cannot_bring_foreign_applications_into_a_scoped_list(client, profile):
    account, _ = MATRIX[profile]
    headers = login(client, account)
    for params in ({"call_id": OTHER_CALL}, {"q": "DATA"}, {"call_id": OTHER_CALL, "limit": 200}):
        items = client.get("/api/v1/applications", headers=headers, params=params).json()["items"]
        assert all(item["program_id"] == OWN_PROGRAM for item in items), params


@pytest.mark.parametrize("account", [ASPIRANTE, CODER])
def test_person_accounts_see_only_their_own_applications(client, db, account):
    headers = login(client, account)
    user = db.scalar(select(User).where(User.email == account))
    client.post("/api/v1/applications", headers=headers, json=new_application(email=user.email))
    own = {str(i) for i in db.scalars(select(Application.id).where(Application.person_id == user.person_id))}
    returned = {item["id"] for item in client.get("/api/v1/me/applications", headers=headers).json()}
    assert returned == own
    assert not returned & set(seed_application_ids(client).values()) - own


@pytest.mark.parametrize("profile", ["captacion", "seleccion"])
def test_out_of_scope_and_unknown_applications_get_the_same_answer(client, profile):
    account, _ = MATRIX[profile]
    headers = login(client, account)
    foreign = seed_application_ids(client)[OTHER_PROGRAM]
    unknown = "00000000-0000-0000-0000-000000000000"
    for method, suffix, body in (("get", "", None), ("post", "/events", {"tipo": "nota", "resumen": "matrix check"})):
        answers = [getattr(client, method)(f"/api/v1/applications/{app_id}{suffix}", headers=headers, **({"json": body} if body else {})) for app_id in (foreign, unknown)]
        assert [a.status_code for a in answers] == [404, 404]
        assert answers[0].json()["detail"] == answers[1].json()["detail"]


@pytest.mark.parametrize("account", [COORD, DOCENTE, ASPIRANTE])
def test_profiles_without_application_access_get_403_for_known_and_unknown_ids(client, account):
    headers = login(client, account)
    for app_id in (seed_application_ids(client)[OWN_PROGRAM], "00000000-0000-0000-0000-000000000000"):
        assert client.get(f"/api/v1/applications/{app_id}", headers=headers).status_code == 403


def test_public_routes_need_no_session(client):
    assert client.get("/health").status_code == 200
    assert client.get("/api/v1/calls").status_code == 200
