from datetime import timedelta

from app.modules.admissions.next_actions import today
from tests.conftest import CAPT_DATA, CAPT_IA, COORD, SEL_IA, login, new_application
from tests.test_contact_next_action import action, contact, user_id

URL = "/api/v1/recruitment/inbox"


def create_application(client, call_id, email):
    response = client.post("/api/v1/applications", json=new_application(call_id=call_id, email=email))
    assert response.status_code == 201, response.text
    return response.json()["id"]


def test_inbox_limits_scope_and_filters_the_latest_action(client, db):
    ia, data = login(client, CAPT_IA), login(client, CAPT_DATA)
    own = create_application(client, "CONV-IA-2027A", "inbox.ia@example.test")
    foreign = create_application(client, "CONV-DATA-2027A", "inbox.data@example.test")
    for application, actor, owner, label, days in (
        (own, ia, CAPT_IA, "Superseded", 0),
        (own, ia, SEL_IA, "Current action", 1),
        (foreign, data, CAPT_DATA, "Foreign action", 1),
    ):
        response = client.post(f"/api/v1/applications/{application}/events", headers=actor,
                               json=contact(action(user_id(db, owner), label, days)))
        assert response.status_code == 201, response.text

    listed = client.get(URL, headers=ia, params={"due_through": str(today() + timedelta(days=1)), "limit": 1})
    assert listed.status_code == 200, listed.text
    [item] = listed.json()["items"]
    assert listed.json()["total"] == 1
    assert item["application_id"] == own and item["action"]["description"] == "Current action"
    assert {"person", "email", "resumen"}.isdisjoint(item)
    for filters in ({"mine": True}, {"due_through": str(today())}, {"offset": 1}):
        assert client.get(URL, headers=ia, params=filters).json()["items"] == []
    assert client.get(URL, headers=data).json()["items"][0]["application_id"] == foreign
    assert client.get(URL, headers=login(client, COORD)).status_code == 403
    assert client.get(URL).status_code == 401

    decision = client.post(f"/api/v1/applications/{own}/preselection-decisions", headers=ia,
                           json={"decision": "convocada", "reason": "Synthetic human handoff"})
    assert decision.status_code == 201, decision.text
    assert client.get(URL, headers=ia).json() == {"items": [], "total": 0}
