"""Parse timestamped transcript cues without executing embedded markup."""
import re
from dataclasses import dataclass

_TIMESTAMP = re.compile(r"(?:(\d{2,}):)?(\d{2}):(\d{2})\.(\d{3})")


@dataclass(frozen=True)
class Cue:
    start_ms: int
    end_ms: int
    text: str


def _milliseconds(value: str) -> int:
    match = _TIMESTAMP.fullmatch(value)
    if not match:
        raise ValueError("Invalid transcript timestamp")
    hours, minutes, seconds, ms = map(int, (part or "0" for part in match.groups()))
    if minutes >= 60 or seconds >= 60:
        raise ValueError("Invalid transcript timestamp")
    return ((hours * 60 + minutes) * 60 + seconds) * 1000 + ms


def parse_webvtt(raw: bytes) -> list[Cue]:
    if len(raw) > 2_000_000:
        raise ValueError("Transcript exceeds size limit")
    text = raw.decode("utf-8-sig").replace("\r\n", "\n").replace("\r", "\n")
    blocks = re.split(r"\n[ \t]*\n", text.strip())
    if not blocks or not re.fullmatch(r"WEBVTT(?:[ \t].*)?", blocks[0].split("\n")[0]):
        raise ValueError("Expected WebVTT transcript")
    cues = []
    for block in blocks[1:]:
        lines = block.split("\n")
        if lines[0] in ("STYLE", "REGION", "NOTE") or lines[0].startswith(("NOTE ", "NOTE\t")):
            continue
        index = 0 if "-->" in lines[0] else 1
        if index >= len(lines) or "-->" not in lines[index]:
            raise ValueError("Missing cue timing")
        start, end = lines[index].split("-->", 1)
        end_parts = end.strip().split()
        if not end_parts:
            raise ValueError("Missing cue end")
        start_ms, end_ms = _milliseconds(start.strip()), _milliseconds(end_parts[0])
        body = "\n".join(lines[index + 1:]).strip()
        if end_ms <= start_ms or not body or len(body) > 8000:
            raise ValueError("Invalid transcript cue")
        cues.append(Cue(start_ms, end_ms, body))
        if len(cues) > 10000:
            raise ValueError("Too many transcript cues")
    return sorted(cues, key=lambda cue: cue.start_ms)
