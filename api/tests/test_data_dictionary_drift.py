"""KAN-107: regression guard for the declared schema. It does NOT read or parse the Markdown dictionary.

The expected sets below are written in Python and mirror the dictionary (PR #24, section 1.1 "Estado en dev"; until
#24 is merged, the canonical document in dev is docs/producto/diccionario-campos-candidatura.md). The test only fails
when the tables and Pydantic schemas stop matching those sets. When that happens the schema changed on purpose or by
accident: in the same change, update the dictionary, the privacy assessment and the expected sets. No database access.
"""

import app.models  # noqa: F401  (registers every table in Base.metadata)
from app.core.db import Base
from app.modules.admissions.schemas import ApplicationCreate, ManualApplicationCreate

# Personal data columns of a person, as listed in the dictionary: one display name, no phone/birth/gender yet.
EXPECTED_PERSON_COLUMNS = {"id", "display_name", "email", "legacy_ref", "is_synthetic", "created_at"}
EXPECTED_APPLICATION_COLUMNS = {
    "id", "codigo", "legacy_ref", "person_id", "call_id", "stage",
    "motivacion", "disponibilidad", "acepta_datos_sinteticos", "created_at", "updated_at",
    "origin_channel", "created_by",  # KAN-275: how the application arrived and which account sent it
}
EXPECTED_CALL_COLUMNS = {
    "id", "program_id", "nombre", "codigo_prefix", "opens_on", "closes_on", "plazas", "estado", "next_seq",
    "silence_days", "silence_max_contacts", "silence_warning_contacts",  # KAN-153: per-call silence policy (30 days / 4 attempts / light alert at 2)
    "selection_quorum",  # Melissa round 3 Q11: people who must agree on a selection decision (default 2)
    "publication_state", "publication_version",  # KAN-226: editorial visibility, not application form versioning
}
EXPECTED_APPLICATION_CREATE_FIELDS = {"call_id", "nombre", "email", "motivacion", "disponibilidad", "acepta_datos_sinteticos"}


# KAN-275: the manual intake collects the same data, plus the channel and the staff confirmation.
EXPECTED_MANUAL_CREATE_FIELDS = (EXPECTED_APPLICATION_CREATE_FIELDS - {"acepta_datos_sinteticos"}) | {"origin_channel", "confirma_datos_sinteticos"}


def column_names(table_name: str) -> set[str]:
    return {column.name for column in Base.metadata.tables[table_name].columns}


def test_person_columns_match_the_dictionary():
    assert column_names("person") == EXPECTED_PERSON_COLUMNS


def test_application_columns_match_the_dictionary():
    assert column_names("application") == EXPECTED_APPLICATION_COLUMNS


def test_call_has_no_form_configuration_yet():
    # Per-call form versioning is only PROPOSED (deliverable 2 of the dictionary PR): a form version column would be a deliberate change.
    assert column_names("call") == EXPECTED_CALL_COLUMNS


def test_public_inscription_form_fields_match_the_dictionary():
    assert set(ApplicationCreate.model_fields) == EXPECTED_APPLICATION_CREATE_FIELDS
    assert set(ManualApplicationCreate.model_fields) == EXPECTED_MANUAL_CREATE_FIELDS


def test_motivation_and_availability_are_still_required_as_the_dictionary_states():
    # PO decided (17-18/11) to make both optional; until that change is implemented the dictionary must keep saying "required".
    application = Base.metadata.tables["application"].columns
    assert application["motivacion"].nullable is False
    assert application["disponibilidad"].nullable is False
    assert ApplicationCreate.model_fields["motivacion"].is_required()
    assert ApplicationCreate.model_fields["disponibilidad"].is_required()


def test_public_form_never_collects_special_category_or_origin_data_yet():
    forbidden = {"phone", "birth_year", "birth_country", "nationality", "gender", "current_situation", "disability_certificate_status"}
    collected = set(ApplicationCreate.model_fields) | set(ManualApplicationCreate.model_fields) | column_names("person") | column_names("application")
    assert collected.isdisjoint(forbidden), "Protected fields appeared: add them to the dictionary groups G3/G6 and the privacy assessment first"
