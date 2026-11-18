"""Deterministic proposals only: no email, database writes or admission decisions."""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import StrEnum
from hashlib import sha256
import json


class TaskKind(StrEnum):
    INFORMATION_SESSION = "information_session"
    EXERCISES = "exercises"
    DOCUMENTATION = "documentation"
    INTERVIEW = "interview"
    REQUIREMENTS = "requirements"
    RESPONSE = "response"


class Action(StrEnum):
    HUMAN_REVIEW = "human_review"
    SIMULATED_REMINDER = "simulated_reminder"


class Reason(StrEnum):
    MISSING_REQUIREMENTS = "missing_requirements"
    RESPONSE_WINDOW_ELAPSED = "response_window_elapsed"
    INFORMATION_SESSION = "information_session"
    EXERCISES = "exercises"
    DOCUMENTATION = "documentation"
    INTERVIEW = "interview"


def identifier(value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("Identifiers must be non-empty strings")
    return value.strip()


@dataclass(frozen=True)
class Task:
    call_id: str
    application_id: str
    task_id: str
    kind: TaskKind
    due_at: datetime
    completed: bool = False
    missing_requirements: tuple[str, ...] = ()

    def __post_init__(self):
        for name in ("call_id", "application_id", "task_id"):
            object.__setattr__(self, name, identifier(getattr(self, name)))
        if type(self.completed) is not bool:
            raise ValueError("Completed must be a boolean")
        if not isinstance(self.missing_requirements, tuple):
            raise ValueError("Missing requirements must be a tuple of identifiers")
        requirements = tuple(sorted({identifier(value) for value in self.missing_requirements}))
        object.__setattr__(self, "missing_requirements", requirements)
        if not isinstance(self.kind, TaskKind):
            raise ValueError("Unknown task kind")
        require_timezone(self.due_at)


@dataclass(frozen=True)
class Policy:
    call_id: str
    version: str
    response_grace: timedelta
    enabled: bool = False
    reminder_delay: timedelta = timedelta(0)
    reminder_lead: timedelta = timedelta(0)

    def __post_init__(self):
        for name in ("call_id", "version"):
            object.__setattr__(self, name, identifier(getattr(self, name)))
        if type(self.enabled) is not bool:
            raise ValueError("Enabled must be a boolean")
        if not all(isinstance(value, timedelta) for value in (self.reminder_delay, self.response_grace, self.reminder_lead)):
            raise ValueError("Delays must be timedeltas")
        if min(self.reminder_delay, self.response_grace, self.reminder_lead) < timedelta(0):
            raise ValueError("Delays cannot be negative")


@dataclass(frozen=True)
class Proposal:
    # This tuple is also the proposed database uniqueness key, never a delivery receipt.
    key: tuple[str, str, str, str, str, str]
    action: Action
    reason: Reason
    proposed_at: datetime


def require_timezone(value: datetime) -> None:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Timezone-aware timestamps are required")


def propose(tasks: list[Task], policy: Policy, now: datetime) -> tuple[Proposal, ...]:
    """Evaluate a call-scoped snapshot. Repeated inputs yield identical operation keys.

    The caller must authorize the scope and atomically persist keys before enqueuing.
    A policy version change permits a new proposal and requires explicit approval.
    """
    require_timezone(now)
    # timedelta policies express elapsed time, not local calendar/wall-clock time.
    # Normalize before arithmetic/comparison: same-zone datetime operations ignore DST/fold.
    now_instant = now.astimezone(timezone.utc)
    if any(task.call_id != policy.call_id for task in tasks):
        raise ValueError("Task outside policy call scope")
    identities = [(task.application_id, task.task_id) for task in tasks]
    if len(set(identities)) != len(identities):
        raise ValueError("Duplicate task in snapshot")
    if not policy.enabled:
        return ()

    proposals = []
    for task in tasks:
        if task.completed:
            continue
        due_instant = task.due_at.astimezone(timezone.utc)
        if task.kind == TaskKind.REQUIREMENTS:
            if not task.missing_requirements:
                continue
            action, reason = Action.HUMAN_REVIEW, Reason.MISSING_REQUIREMENTS
        elif task.kind == TaskKind.RESPONSE:
            if now_instant < due_instant + policy.response_grace:
                continue
            action, reason = Action.HUMAN_REVIEW, Reason.RESPONSE_WINDOW_ELAPSED
        elif task.kind == TaskKind.INFORMATION_SESSION:
            # Pre-session window only; no stale invitation reminder after the appointment.
            if not due_instant - policy.reminder_lead <= now_instant < due_instant:
                continue
            action, reason = Action.SIMULATED_REMINDER, Reason.INFORMATION_SESSION
        else:
            if now_instant < due_instant + policy.reminder_delay:
                continue
            action, reason = Action.SIMULATED_REMINDER, Reason(task.kind.value)
        revision = sha256(json.dumps([task.kind.value, task.missing_requirements], separators=(",", ":")).encode()).hexdigest()
        key = (task.call_id, task.application_id, task.task_id, policy.version, action.value, revision)
        proposals.append(Proposal(key, action, reason, now))
    return tuple(proposals)
