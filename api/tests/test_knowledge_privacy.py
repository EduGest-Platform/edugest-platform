"""KAN-130: the detector finds emails, DNI/NIE, Spanish phones and registered full names, and reports only the kind."""

import pytest

from app.core.config import settings
from app.modules.knowledge.corpus import load_corpus
from app.modules.knowledge.privacy import find_personal_data
from app.seed import load_seed

NAMES = ["Lucía Moreno Vidal", "Persona Sintética"]


@pytest.mark.parametrize(
    ("text", "kind"),
    [
        ("Escribe a tutoria@example.test para dudas.", "email"),
        ("Contacto: nombre.apellido+curso@escuela.example.test", "email"),
        ("DNI 12345678Z en el expediente.", "dni_nie"),
        ("NIE X1234567L.", "dni_nie"),
        ("Documento 12345678-z", "dni_nie"),
        ("Llama al 612345678.", "phone"),
        ("Teléfono: +34 612 345 678", "phone"),
        ("Fijo 0034 912-345-678", "phone"),
        ("Hoy expone Lucía Moreno Vidal.", "person_name"),
        ("hoy expone LUCIA moreno  vidal", "person_name"),  # case, accents and spacing do not matter
        ("Persona\nSintética entrega el viernes.", "person_name"),  # a line break between the words
    ],
)
def test_each_kind_of_personal_data_is_found(text, kind):
    assert find_personal_data(text, NAMES) == [kind]


@pytest.mark.parametrize(
    "text",
    [
        "Llegar más de una hora tarde cuenta como media jornada: 0,5 faltas.",
        "La entrega es el 2026-12-04 a las 18:00 en la sala 12.",
        "Plazo de 48 horas. Código de convocatoria CONV-IA-2027A.",
        "El presupuesto es de 123456789 euros.",  # 9 digits that cannot be a Spanish phone
        "Lucía explicará el ejercicio.",  # a single first name is not checked (documented limit)
        "Envía la práctica por la plataforma (@usuario no es un email).",
    ],
)
def test_ordinary_course_text_is_clean(text):
    assert find_personal_data(text, NAMES) == []


def test_several_kinds_are_reported_once_each_and_never_the_value():
    found = find_personal_data("Lucía Moreno Vidal (lucia@example.test, 612 345 678, 12345678Z)", NAMES)
    assert found == ["email", "dni_nie", "phone", "person_name"]
    assert not any("@" in kind or any(ch.isdigit() for ch in kind) for kind in found)


def test_single_word_names_are_ignored_to_avoid_false_positives():
    assert find_personal_data("Ana revisa la entrega.", ["Ana"]) == []


def test_a_name_inside_a_longer_word_does_not_match():
    assert find_personal_data("Persona Sintéticamente correcta.", ["Persona Sintética"]) == []


def test_the_real_corpus_is_clean_with_every_synthetic_name_of_the_seed():
    # Alarm: if a new seed (KAN-173) adds names that collide with course text, this fails in CI, not in the demo.
    seed = load_seed()
    names = [p["nombre_ficticio"] for p in seed["candidaturas"] + seed["coders"]]
    documents, _ = load_corpus(settings.corpus_path)
    assert {d.source_key: find_personal_data(d.text, names) for d in documents} == {d.source_key: [] for d in documents}
