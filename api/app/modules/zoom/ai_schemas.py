"""Opt-in meeting intelligence contracts; no external processing is performed here."""
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class SessionAISettings(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    cloud_recording: bool = False
    transcription: bool = False
    notes: bool = False
    action_items: bool = False
    quizzes: bool = False
    rag_indexing: bool = False
    visibility: Literal["teachers", "cohort", "coordination"] = "teachers"

    @model_validator(mode="after")
    def validate_dependencies(self):
        if self.transcription and not self.cloud_recording:
            raise ValueError("Transcription requires cloud recording")
        if self.notes and not self.transcription:
            raise ValueError("Notes require transcription")
        if (self.action_items or self.quizzes or self.rag_indexing) and not self.notes:
            raise ValueError("Derived artifacts require notes")
        return self


class EvidenceSpan(BaseModel):
    model_config = ConfigDict(extra="forbid")
    start_seconds: int = Field(ge=0)
    end_seconds: int = Field(ge=0)

    @model_validator(mode="after")
    def validate_order(self):
        if self.end_seconds < self.start_seconds:
            raise ValueError("Invalid evidence interval")
        return self


class NoteItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: str = Field(min_length=1, max_length=4000)
    evidence: list[EvidenceSpan] = Field(min_length=1, max_length=20)


class ActionItem(NoteItem):
    # Suggestions only; never create an assignment automatically.
    proposed_owner: str | None = Field(default=None, max_length=200)
    proposed_due_date: str | None = Field(default=None, max_length=100)


class MeetingNotesDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")
    summary: list[NoteItem] = Field(max_length=30)
    key_topics: list[NoteItem] = Field(default_factory=list, max_length=50)
    reinforcement_topics: list[NoteItem] = Field(default_factory=list, max_length=30)
    action_items: list[ActionItem] = Field(default_factory=list, max_length=50)
    # Publication and review state must be assigned by the authorized server,
    # not accepted from the generative provider.
