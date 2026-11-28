import pytest
from pydantic import ValidationError

from app.modules.zoom.ai_schemas import MeetingNotesDraft, SessionAISettings


def test_ai_disabled_by_default():
    settings = SessionAISettings()
    assert not any((settings.cloud_recording, settings.transcription, settings.notes,
                    settings.action_items, settings.quizzes, settings.rag_indexing))
    assert settings.visibility == "teachers"


@pytest.mark.parametrize("kwargs", [
    {"transcription": True},
    {"notes": True},
    {"action_items": True},
    {"quizzes": True},
    {"rag_indexing": True},
])
def test_ai_dependencies(kwargs):
    with pytest.raises(ValidationError):
        SessionAISettings(**kwargs)


def test_valid_opt_in():
    assert SessionAISettings(cloud_recording=True, transcription=True,
                             notes=True, rag_indexing=True).rag_indexing


def test_notes_require_evidence():
    with pytest.raises(ValidationError):
        MeetingNotesDraft(summary=[{"text": "Example", "evidence": []}])
    with pytest.raises(ValidationError):
        MeetingNotesDraft(summary=[{"text": "Example", "evidence": [
            {"start_seconds": 10, "end_seconds": 5}]}])


def test_provider_cannot_publish_notes():
    with pytest.raises(ValidationError):
        MeetingNotesDraft(summary=[], published=True)
