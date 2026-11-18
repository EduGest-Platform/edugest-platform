"""KAN-118: edge cases of application creation and search that the happy-path tests do not reach."""

import pytest
from sqlalchemy import event, func, select

from app.core.db import SessionLocal
from app.modules.admissions.models import Application
from app.modules.identity.models import Person
from tests.conftest import ADMIN, login, new_application

SECOND_OPEN_CALL = "CONV-DATA-2027A"


@pytest.fixture
def competing_person_insert():
    """Simulates another request that creates the same Person and commits right after our lookup."""
    state = {"email": None, "done": False}

    def insert_competitor(mapper, connection, target):
        if state["done"] or target.email != state["email"]:
            return
        state["done"] = True
        with SessionLocal() as other:
            other.add(Person(display_name="Competing Request", email=target.email, is_synthetic=True))
            other.commit()

    event.listen(Person, "before_insert", insert_competitor)
    yield state
    event.remove(Person, "before_insert", insert_competitor)


def test_same_new_email_created_concurrently_reuses_the_person_instead_of_failing(client, db, competing_person_insert):
    email = "carrera.persona@example.test"
    competing_person_insert["email"] = email
    response = client.post("/api/v1/applications", json=new_application(email=email, call_id=SECOND_OPEN_CALL))
    assert response.status_code == 201, response.text
    assert db.scalar(select(func.count()).select_from(Person).where(Person.email == email)) == 1
    application = db.scalar(select(Application).where(Application.id == response.json()["id"]))
    assert application.person_id == db.scalar(select(Person.id).where(Person.email == email))


@pytest.mark.parametrize("wildcard_query", ["%", "_", "\\", "50%"])
def test_search_treats_percent_underscore_and_backslash_as_plain_text(client, wildcard_query):
    headers = login(client, ADMIN)
    assert client.post("/api/v1/applications", json=new_application()).status_code == 201
    everything = client.get("/api/v1/applications", headers=headers).json()["total"]
    assert everything > 0
    found = client.get("/api/v1/applications", params={"q": wildcard_query}, headers=headers)
    assert found.status_code == 200
    assert found.json()["total"] == 0


def test_search_still_finds_by_name_email_and_code(client):
    headers = login(client, ADMIN)
    created = client.post("/api/v1/applications", json=new_application(nombre="Búsqueda Sintética", email="busqueda.sintetica@example.test")).json()
    for query in ["búsqueda sint", "busqueda.sintetica@", created["codigo"].lower()]:
        items = client.get("/api/v1/applications", params={"q": query}, headers=headers).json()["items"]
        assert [i["id"] for i in items] == [created["id"]]
