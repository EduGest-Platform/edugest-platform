"""Provider-independent generation boundary for reviewable meeting notes."""
from collections.abc import Callable
from typing import Any

from app.modules.zoom.ai_schemas import MeetingNotesDraft, SessionAISettings
from app.modules.zoom.transcript import Cue


def generate_draft(settings: SessionAISettings, cues: list[Cue],
                   generate: Callable[[list[dict]], Any]) -> MeetingNotesDraft:
    if not settings.notes or not settings.transcription or not settings.cloud_recording:
        raise ValueError("Meeting notes are not enabled")
    if not cues or len(cues) > 10000:
        raise ValueError("Invalid transcript cue count")
    if sum(len(cue.text) for cue in cues) > 100000:
        raise ValueError("Transcript exceeds generation budget")
    if any(cue.start_ms < 0 or cue.end_ms <= cue.start_ms or not cue.text.strip() for cue in cues):
        raise ValueError("Invalid transcript cue")
    # Transcript text is untrusted data, never instructions. The provider adapter
    # must enforce this boundary and must not expose tools or other session data.
    payload = [{"start_seconds": cue.start_ms // 1000,
                "end_seconds": (cue.end_ms + 999) // 1000,
                "text": cue.text} for cue in cues]
    draft = MeetingNotesDraft.model_validate(generate(payload))
    if draft.action_items and not settings.action_items:
        raise ValueError("Action items are not enabled")
    allowed = {(item["start_seconds"], item["end_seconds"]) for item in payload}
    for item in (*draft.summary, *draft.key_topics, *draft.reinforcement_topics, *draft.action_items):
        for span in item.evidence:
            if (span.start_seconds, span.end_seconds) not in allowed:
                raise ValueError("Evidence does not match a transcript cue")
    # Matching timestamps does not establish semantic accuracy. Human review
    # remains mandatory before publication or indexing.
    return draft
