"""Splits a course document into retrievable passages (KAN-130).

One chunk per paragraph (text between blank lines). Each chunk starts with the document title, and the
section heading when there is one, so a short passage such as «0,5 faltas» keeps its context for keyword
and semantic search. Markdown headings are not chunks of their own. Paragraphs longer than MAX_CHARS are
split on sentence boundaries, never in the middle of a sentence unless a single sentence is too long.
"""

from __future__ import annotations

import re

MAX_CHARS = 1500
HEADING = re.compile(r"^#{1,6}\s+(.+)$")
SENTENCE_END = re.compile(r"(?<=[.!?])\s+")


def split_into_chunks(title: str, text: str) -> list[str]:
    chunks: list[str] = []
    section: str | None = None
    for block in _blocks(text):
        lines = block.splitlines()
        while lines and (match := HEADING.match(lines[0].strip())):
            heading = match.group(1).strip()
            section = None if heading.casefold() == title.casefold() else heading
            lines = lines[1:]
        body = "\n".join(lines).strip()
        if not body:
            continue
        prefix = f"{title} · {section}" if section else title
        chunks.extend(f"{prefix}: {piece}" for piece in _limit(body))
    return chunks


def _blocks(text: str) -> list[str]:
    return [block.strip() for block in re.split(r"\n\s*\n", text.replace("\r\n", "\n")) if block.strip()]


def _limit(body: str) -> list[str]:
    if len(body) <= MAX_CHARS:
        return [body]
    pieces: list[str] = []
    current = ""
    for sentence in SENTENCE_END.split(body):
        while len(sentence) > MAX_CHARS:  # a single sentence that is too long: hard split as a last resort
            if current:
                pieces.append(current)
                current = ""
            pieces.append(sentence[:MAX_CHARS])
            sentence = sentence[MAX_CHARS:]
        candidate = f"{current} {sentence}".strip()
        if len(candidate) > MAX_CHARS:
            pieces.append(current)
            current = sentence
        else:
            current = candidate
    if current:
        pieces.append(current)
    return pieces
