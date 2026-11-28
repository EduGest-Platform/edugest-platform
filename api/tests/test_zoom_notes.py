import pytest

from app.modules.zoom.ai_schemas import SessionAISettings
from app.modules.zoom.notes import generate_draft
from app.modules.zoom.transcript import parse_webvtt


RAW = b"WEBVTT\n\n00:00:01.000 --> 00:00:03.500\nReact components\n"
ENABLED = SessionAISettings(cloud_recording=True, transcription=True, notes=True)


def test_parse_and_generate():
    cues = parse_webvtt(RAW)
    assert cues[0].start_ms == 1000
    assert cues[0].end_ms == 3500
    draft = generate_draft(ENABLED, cues, lambda payload: {
        "summary": [{"text": payload[0]["text"], "evidence": [
            {"start_seconds": 1, "end_seconds": 4}]}]
    })
    assert draft.summary[0].text == "React components"


def test_reject_unknown_evidence():
    with pytest.raises(ValueError, match="Evidence"):
        generate_draft(ENABLED, parse_webvtt(RAW), lambda _: {
            "summary": [{"text": "Unsupported", "evidence": [
                {"start_seconds": 10, "end_seconds": 20}]}]
        })


def test_disabled_does_not_call_provider():
    def provider(_):
        pytest.fail("Provider called despite disabled notes")
    with pytest.raises(ValueError, match="not enabled"):
        generate_draft(SessionAISettings(), parse_webvtt(RAW), provider)


def test_invalid_transcript():
    with pytest.raises(ValueError):
        parse_webvtt(b"not a transcript")
    with pytest.raises(ValueError):
        parse_webvtt(b"WEBVTT\n\n00:00:03.000 --> 00:00:01.000\nInvalid")
