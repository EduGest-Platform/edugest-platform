"""KAN-130: one chunk per paragraph, with the document title (and section) as context; long paragraphs split by sentence."""

from app.core.config import settings
from app.modules.knowledge.chunking import MAX_CHARS, split_into_chunks
from app.modules.knowledge.corpus import load_corpus


def test_every_real_document_gives_chunks_that_start_with_its_title():
    documents, _ = load_corpus(settings.corpus_path)
    for document in documents:
        chunks = split_into_chunks(document.title, document.text)
        assert chunks, document.source_key
        assert all(chunk.startswith(document.title) for chunk in chunks)
        assert not any(chunk.split(": ", 1)[1].startswith("#") for chunk in chunks)


def test_a_short_rule_keeps_its_context():
    documents, _ = load_corpus(settings.corpus_path)
    a4 = next(d for d in documents if d.source_key == "A4")
    chunks = split_into_chunks(a4.title, a4.text)
    assert len(chunks) == 5
    assert any(chunk.startswith("Normas de asistencia: ") and "0,5 faltas" in chunk for chunk in chunks)


def test_the_main_heading_is_not_a_chunk_nor_repeated():
    text = "# Guía\n\nPrimer párrafo.\n\nSegundo párrafo."
    assert split_into_chunks("Guía", text) == ["Guía: Primer párrafo.", "Guía: Segundo párrafo."]


def test_section_headings_give_context_to_the_paragraphs_below():
    text = "# Guía\n\n## Entrega\n\nSe entrega el viernes.\n\n## Evaluación\nSe evalúa con rúbrica.\n\nHay dos intentos."
    assert split_into_chunks("Guía", text) == [
        "Guía · Entrega: Se entrega el viernes.",
        "Guía · Evaluación: Se evalúa con rúbrica.",
        "Guía · Evaluación: Hay dos intentos.",
    ]


def test_windows_line_endings_and_extra_blank_lines_are_ignored():
    assert split_into_chunks("T", "Uno.\r\n\r\n\r\n  \r\nDos.") == ["T: Uno.", "T: Dos."]


def test_a_document_with_only_headings_gives_no_chunks():
    assert split_into_chunks("T", "# T\n\n## Vacío") == []


def test_long_paragraphs_are_split_on_sentence_boundaries():
    paragraph = ("Esta es una frase sintética de prueba con bastante texto. " * 60).strip()
    bodies = [chunk.removeprefix("T: ") for chunk in split_into_chunks("T", paragraph)]
    assert len(bodies) >= 3
    assert all(len(body) <= MAX_CHARS and body.endswith(".") for body in bodies)
    assert " ".join(bodies) == paragraph  # nothing is lost or duplicated


def test_a_single_sentence_longer_than_the_limit_is_cut_as_a_last_resort():
    sentence = "x" * (MAX_CHARS * 2 + 10)
    bodies = [chunk.removeprefix("T: ") for chunk in split_into_chunks("T", sentence)]
    assert [len(body) for body in bodies] == [MAX_CHARS, MAX_CHARS, 10]
    assert "".join(bodies) == sentence


def test_the_same_input_always_gives_the_same_chunks():
    text = "# T\n\nUno.\n\n## S\n\nDos."
    assert split_into_chunks("T", text) == split_into_chunks("T", text)
