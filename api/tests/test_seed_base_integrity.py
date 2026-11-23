"""KAN-131: base seed integrity and non-destructive CLI reruns on disposable PostgreSQL."""

import sys

from sqlalchemy import func, select

from app import seed as seed_module
from app.core.db import Base, utcnow
from app.modules.admissions.models import Application, ApplicationEvent
from app.modules.catalog.models import Call, Cohort, Program
from app.modules.identity.models import Person, RoleAssignment, User
from app.modules.learning.models import Enrollment
from tests.conftest import CAPT_IA, login, new_application


def identities(db):
    """IDs only: never snapshot credentials, tokens or captured application content."""
    db.expire_all()
    return {table.name: set(db.execute(select(*table.primary_key.columns)).all())
            for table in Base.metadata.sorted_tables}


def test_seed_catalog_keeps_call_program_and_cohort_bindings(db):
    data = seed_module.load_seed()
    assert set(db.scalars(select(Program.id))) == {item["id"] for item in data["programas"]}
    calls = {call.id: call for call in db.scalars(select(Call))}
    assert set(calls) == {row[0] for row in seed_module.CALLS}
    for call_id, program_id, _, prefix, opens, closes, places, state, cohort_id in seed_module.CALLS:
        call = calls[call_id]
        assert (call.program_id, call.codigo_prefix, call.opens_on, call.closes_on, call.plazas, call.estado) == (
            program_id, prefix, opens, closes, places, state,
        )
        if cohort_id:
            cohort = db.get(Cohort, cohort_id)
            assert (cohort.program_id, cohort.call_id) == (program_id, call_id)
    # seed.json cohorts plus the upcoming ones fed by the open calls (so the demo can admit and enroll).
    upcoming = {row[0] for row in seed_module.UPCOMING_COHORTS}
    assert {cohort.id for cohort in db.scalars(select(Cohort))} == {item["id"] for item in data["cohortes"]} | upcoming
    for cohort_id, program_id, call_id, *_ in seed_module.UPCOMING_COHORTS:
        cohort = db.get(Cohort, cohort_id)
        assert (cohort.program_id, cohort.call_id) == (program_id, call_id) and calls[call_id].program_id == program_id


def test_seed_people_keep_source_references_and_synthetic_identity(db):
    data = seed_module.load_seed()
    expected = {item["id"]: item for item in data["candidaturas"] + data["coders"]}
    people = {person.legacy_ref: person for person in db.scalars(select(Person))}
    assert set(people) == set(expected)
    for ref, source in expected.items():
        person = people[ref]
        assert person.is_synthetic
        assert person.email == source["email_demo"].lower()
        assert person.display_name == source["nombre_ficticio"]
    assert len({person.email for person in people.values()}) == len(people)


def test_seed_applications_preserve_states_without_importing_browser_drafts(db):
    data = seed_module.load_seed()
    expected = {item["id"]: item for item in data["candidaturas"] if item["estado"] != "borrador"}
    applications = {application.legacy_ref: application for application in db.scalars(select(Application))}
    assert set(applications) == set(expected)
    for ref, source in expected.items():
        application = applications[ref]
        person = db.get(Person, application.person_id)
        assert person.legacy_ref == ref
        assert application.call_id == seed_module.OPEN_CALL[source["programa_id"]]
        assert application.stage == source["estado"]
        assert application.acepta_datos_sinteticos
        events = list(db.scalars(select(ApplicationEvent).where(ApplicationEvent.application_id == application.id)))
        assert len(events) == 1 and events[0].tipo == "creada"
    assert {application.stage for application in applications.values()} == {item["estado"] for item in expected.values()}
    for call in db.scalars(select(Call)):
        codes = [item.codigo for item in applications.values() if item.call_id == call.id]
        assert len(codes) == len(set(codes))
        assert all(code.startswith(call.codigo_prefix + "-") for code in codes)
        assert call.next_seq == len(codes) + 1


def test_seed_staff_roles_keep_the_declared_scope_without_extra_grants(db):
    users = {user.email: user for user in db.scalars(select(User))}
    expected_users = {row[0] for row in seed_module.STAFF}
    for email, _, roles in seed_module.STAFF:
        user = users[email]
        assert user.is_active and user.person_id is None
        assignments = list(db.scalars(select(RoleAssignment).where(RoleAssignment.user_id == user.id)))
        assert {(row.role, row.scope_type, row.scope_id) for row in assignments} == set(roles)
        assert all(row.revoked_at is None for row in assignments)
    assert set(users) - expected_users == {
        db.scalar(select(Person.email).where(Person.legacy_ref == ref)) for ref in seed_module.PERSON_USERS
    }


def test_seed_person_logins_and_enrollments_reuse_people_without_staff_roles(db):
    for ref in seed_module.PERSON_USERS:
        person = db.scalars(select(Person).where(Person.legacy_ref == ref)).one()
        user = db.scalars(select(User).where(User.person_id == person.id)).one()
        assert user.email == person.email and user.is_active
        assert db.scalar(select(func.count()).select_from(RoleAssignment).where(RoleAssignment.user_id == user.id)) == 0
    expected = {(item["id"], item["cohorte_id"]) for item in seed_module.load_seed()["coders"]}
    rows = db.execute(select(Person.legacy_ref, Enrollment.cohort_id, Enrollment.estado)
                      .join(Enrollment, Enrollment.person_id == Person.id)).all()
    assert {(ref, cohort_id) for ref, cohort_id, _ in rows} == expected
    assert len(rows) == len(expected) and all(state == "activa" for _, _, state in rows)


def test_normal_cli_rerun_preserves_later_intake_contacts_and_manual_changes(client, db, monkeypatch):
    monkeypatch.setattr(sys, "argv", ["app.seed"])
    response = client.post("/api/v1/applications", json=new_application(email="seed.rerun@example.test"))
    assert response.status_code == 201
    application_id = response.json()["id"]
    actor = login(client, CAPT_IA)
    contact = client.post(f"/api/v1/applications/{application_id}/events", headers=actor, json={
        "tipo": "contacto", "canal": "telefono", "resultado": "respondida", "resumen": "Synthetic contact after seeding",
    })
    assert contact.status_code == 201
    call = db.get(Call, "CONV-IA-2027A")
    call.plazas += 3
    places = call.plazas
    assignment = db.scalars(select(RoleAssignment).where(RoleAssignment.role == "captacion", RoleAssignment.scope_id == "P-DATA")).one()
    assignment.revoked_at = utcnow()
    revoked_at = assignment.revoked_at
    assignment_id = assignment.id
    db.commit()

    # Reconcile academic reference data once, then compare the complete database identity graph.
    seed_module.main()
    before = identities(db)

    def forbidden_reset(*_args):
        raise AssertionError("A normal seed rerun must not reset data")

    monkeypatch.setattr(seed_module, "reset", forbidden_reset)
    seed_module.main()
    assert identities(db) == before
    assert db.get(Call, call.id).plazas == places
    assert db.get(RoleAssignment, assignment_id).revoked_at == revoked_at
    dossier = client.get(f"/api/v1/applications/{application_id}", headers=actor)
    assert dossier.status_code == 200
    assert dossier.json()["stage"] == "enviada"
    assert contact.json()["id"] in {event["id"] for event in dossier.json()["events"]}


def test_cli_bootstraps_an_empty_test_database_and_a_second_run_reuses_all_ids(db, monkeypatch):
    monkeypatch.setattr(sys, "argv", ["app.seed"])
    # This fixture already guarantees an isolated PostgreSQL test database; never use a shared DB.
    seed_module.reset(db)
    seed_module.main()
    first = identities(db)
    assert first["program"] and first["application"] and first["enrollment"]
    assert first["attendance_record"] and first["competency_assessment"]
    seed_module.main()
    assert identities(db) == first
