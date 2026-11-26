"""Compose transcript parsing, generation and evidence validation without publishing."""
import httpx

from app.modules.zoom.ai_schemas import MeetingNotesDraft, SessionAISettings
from app.modules.zoom.generator import GenerationError, generate_notes
from app.modules.zoom.notes import generate_draft
from app.modules.zoom.transcript import parse_webvtt


def build_notes_draft(
    raw: bytes, session_settings: SessionAISettings, *,
    client: httpx.Client, api_key: str, model: str,
    synthetic_data_authorized: bool = False,
) -> MeetingNotesDraft:
    if not synthetic_data_authorized or not api_key:
        raise GenerationError("Meeting generation not authorized")
    if not session_settings.notes:
        raise ValueError("Meeting notes are not enabled")
    cues = parse_webvtt(raw)
    return generate_draft(
        session_settings, cues,
        lambda payload: generate_notes(
            client, api_key=api_key, model=model, cues=payload,
            synthetic_data_authorized=synthetic_data_authorized,
        ),
    )
