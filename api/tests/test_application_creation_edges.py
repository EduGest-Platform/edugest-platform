"""KAN-118: edge cases of application creation and search that the happy-path tests do not reach."""

import pytest

from tests.conftest import ADMIN, login, new_application


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
