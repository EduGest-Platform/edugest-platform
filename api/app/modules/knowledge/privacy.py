"""Detects personal data in course documents before they enter the knowledge base (KAN-130).

Fail closed: the pipeline rejects a document with any finding. Findings are only the kind of data,
never the value, so they can be written to logs and audit events safely.

Known limit: names are detected only when they match a registered person's full name (two or more words).
Unregistered names need an NER detector such as Microsoft Presidio (future work, not implemented).
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable

EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
# DNI: 8 digits + control letter. NIE: X, Y or Z + 7 digits + control letter. Optional space or dash before the letter.
DNI_NIE = re.compile(r"(?<![\w])(?:\d{8}|[XYZ]\d{7})[\s-]?[A-HJ-NP-TV-Z](?![\w])", re.IGNORECASE)
# Spanish phone: optional +34 / 0034, then 9 digits starting with 6, 7, 8 or 9, with optional spaces or dashes.
PHONE = re.compile(r"(?<!\d)(?:(?:\+|00)34[\s-]?)?[6-9](?:[\s-]?\d){8}(?!\d)")
MIN_NAME_WORDS = 2


def find_personal_data(text: str, known_names: Iterable[str] = ()) -> list[str]:
    """Returns the kinds of personal data found in the text, for example ["email", "phone"]. Empty means clean."""
    found = []
    if EMAIL.search(text):
        found.append("email")
    if DNI_NIE.search(text):
        found.append("dni_nie")
    if PHONE.search(text):
        found.append("phone")
    if _contains_known_name(text, known_names):
        found.append("person_name")
    return found


def _normalize(value: str) -> str:
    """Lower case, no accents and single spaces, so «Lucía  MORENO» matches «lucia moreno»."""
    decomposed = unicodedata.normalize("NFKD", value)
    without_accents = "".join(c for c in decomposed if not unicodedata.combining(c))
    return " ".join(without_accents.casefold().split())


def _contains_known_name(text: str, known_names: Iterable[str]) -> bool:
    haystack = _normalize(text)
    for name in known_names:
        needle = _normalize(name)
        if len(needle.split()) < MIN_NAME_WORDS:
            continue  # a single first name would reject ordinary documents
        if re.search(rf"(?<!\w){re.escape(needle)}(?!\w)", haystack):
            return True
    return False
