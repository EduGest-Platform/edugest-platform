import json

import httpx
import pytest

from app.modules.zoom.ai_schemas import SessionAISettings
from app.modules.zoom.generator import GenerationError
from app.modules.zoom.notes_service import build_notes_draft

RAW = b"WEBVTT\n\n00:00:01.000 --> 00:00:03.000\nSynthetic lesson\n"
SETTINGS = SessionAISettings(cloud_recording=True, transcription=True, notes=True)


def test_notes_pipeline():
    def handler(request):
        assert request.url.host == "generativelanguage.googleapis.com"
        assert request.headers["x-goog-api-key"] == "fake-key"
        draft = {"summary": [{"text": "Synthetic lesson", "evidence": [
            {"start_seconds": 1, "end_seconds": 3}]}]}
        return httpx.Response(200, json={"candidates": [{"finishReason": "STOP",
            "content": {"parts": [{"text": json.dumps(draft)}]}}]})
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        result = build_notes_draft(RAW, SETTINGS, client=client, api_key="fake-key",
                                   model="gemini-test", synthetic_data_authorized=True)
    assert result.summary[0].text == "Synthetic lesson"


def test_no_authorization_no_network():
    def handler(request):
        pytest.fail("Unexpected provider call")
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(GenerationError):
            build_notes_draft(RAW, SETTINGS, client=client, api_key="fake-key", model="gemini-test")


def test_provider_failure_is_sanitized():
    with httpx.Client(transport=httpx.MockTransport(
        lambda request: httpx.Response(503, text="private provider details")
    )) as client:
        with pytest.raises(GenerationError, match="provider rejected"):
            build_notes_draft(RAW, SETTINGS, client=client, api_key="fake-key",
                              model="gemini-test", synthetic_data_authorized=True)
