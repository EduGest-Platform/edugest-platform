from uuid import uuid4

from app.core.config import settings
from app.core.security import hash_password
from app.modules.catalog.models import Call
from app.modules.identity.models import Person, User
from tests.conftest import ADMIN, ASPIRANTE, COORD, SEL_IA, login
from tests.test_selection_decisions import IA_CALL, decide, make_application


def own_outcome_path(application_id):
    return f"/api/v1/me/applications/{application_id}/selection-outcome"


def create_applicant_account(db, application):
    person = db.get(Person, application.person_id)
    db.add(User(
        person_id=person.id, email=person.email, display_name=person.display_name,
        password_hash=hash_password(settings.demo_password),
    ))
    db.commit()
    return person.email


def test_applicant_sees_only_the_applied_outcome_without_internal_vote_details(client, db):
    application = make_application(db, stage="convocada")
    owner = login(client, create_applicant_account(db, application))
    path = own_outcome_path(application.id)
    expected = {"application_id": str(application.id), "stage": "convocada", "outcome": None, "decided_at": None}
    assert client.get(path, headers=owner).json() == expected
    assert db.get(Call, IA_CALL).selection_quorum == 2

    first = decide(client, login(client, SEL_IA), application.id, "no_admitida", reason="Synthetic internal reason")
    assert first.status_code == 202
    assert client.get(path, headers=owner).json() == {**expected, "stage": "pendiente_decision_humana"}

    final = decide(client, login(client, COORD), application.id, "no_admitida", reason="Synthetic signed reason")
    assert final.status_code == 201
    private = client.get(path, headers=owner)
    assert private.status_code == 200 and private.headers["cache-control"] == "no-store"
    assert private.json() == {
        **expected, "stage": "no_admitida", "outcome": "no_admitida", "decided_at": final.json()["occurred_at"],
    }


def test_foreign_and_missing_applications_share_the_same_error(client, db):
    application = make_application(db, stage="lista_espera")
    path = own_outcome_path(application.id)
    assert client.get(path).status_code == 401
    for account in (ASPIRANTE, ADMIN):
        actor = login(client, account)
        other = client.get(path, headers=actor)
        absent = client.get(own_outcome_path(uuid4()), headers=actor)
        assert other.status_code == absent.status_code == 404
        assert other.json()["code"] == absent.json()["code"] == "application_not_found"
