"""KAN-124: text validation boundaries, runnable without a database or API fixtures."""

import pytest
from pydantic import ValidationError

from app.modules.admissions.schemas import ApplicationCreate, EventCreate


def parse_text(field, value):
    if field == "resumen":
        return EventCreate(tipo="nota", resumen=value).resumen
    payload = {
        "call_id": "CONV-SYNTHETIC",
        "nombre": "Synthetic Applicant",
        "email": "synthetic@example.test",
        "motivacion": "Synthetic application text.",
        "disponibilidad": "Tarde",
        "acepta_datos_sinteticos": True,
    }
    payload[field] = value
    return getattr(ApplicationCreate(**payload), field)


@pytest.mark.parametrize("field", ["nombre", "motivacion", "resumen"])
@pytest.mark.parametrize("value", [" " * 10, "\t\n" * 5, "\u00a0" * 10])
def test_blank_text_is_rejected(field, value):
    with pytest.raises(ValidationError) as error:
        parse_text(field, value)
    assert error.value.errors()[0]["loc"] == (field,)


@pytest.mark.parametrize("field,value", [("nombre", " A "), ("motivacion", " " + "M" * 9 + " ")])
def test_padding_cannot_satisfy_minimum_length(field, value):
    with pytest.raises(ValidationError) as error:
        parse_text(field, value)
    assert error.value.errors()[0]["type"] == "string_too_short"


@pytest.mark.parametrize("field,size", [("nombre", 2), ("nombre", 120), ("motivacion", 10), ("motivacion", 2000), ("resumen", 1), ("resumen", 500)])
def test_padded_exact_boundaries_are_normalized_and_accepted(field, size):
    content = "X" * size
    assert parse_text(field, " \t\u00a0" + content + "\u00a0\n ") == content


@pytest.mark.parametrize("field,maximum", [("nombre", 120), ("motivacion", 2000), ("resumen", 500)])
def test_normalized_text_above_maximum_is_rejected(field, maximum):
    with pytest.raises(ValidationError) as error:
        parse_text(field, " " + "X" * (maximum + 1) + " ")
    assert error.value.errors()[0]["type"] == "string_too_long"


@pytest.mark.parametrize("field", ["nombre", "motivacion", "resumen"])
@pytest.mark.parametrize("value", [None, 123, True, [], {}])
def test_non_string_inputs_remain_validation_errors(field, value):
    with pytest.raises(ValidationError) as error:
        parse_text(field, value)
    assert error.value.errors()[0]["loc"] == (field,)
    assert error.value.errors()[0]["type"] == "string_type"


@pytest.mark.parametrize("field", ["nombre", "motivacion", "resumen"])
def test_internal_whitespace_is_preserved(field):
    assert parse_text(field, "  Synthetic  text\tinside  ") == "Synthetic  text\tinside"
