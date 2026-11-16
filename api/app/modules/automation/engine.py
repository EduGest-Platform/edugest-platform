"""Deterministic proposals only: no email, database writes or admission decisions."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum


class TaskKind(StrEnum):
    INFORMATION_SESSION = "information_session"
    EXERCISES = "exercises"
    DOCUMENTATION = "documentation"
    INTERVIEW = "interview"
    REQUIREMENTS = "requirements"
    RESPONSE = "response"


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
        if not all((self.call_id.strip(), self.application_id.strip(), self.task_id.strip())):
            raise ValueError("Call, application and task identifiers are required")
        if not isinstance(self.kind, TaskKind):
            raise ValueError("Unknown task kind")
        require_timezone(self.due_at)


@dataclass(frozen=True)
class Policy:
    call_id: str
    version: str
    enabled: bool = False
    reminder_delay: timedelta = timedelta(0)
    response_grace: timedelta = timedelta(days=7)

    def __post_init__(self):
        if not self.call_id.strip() or not self.version.strip():
            raise ValueError("Call and policy version are required")
        if self.reminder_delay < timedelta(0) or self.response_grace < timedelta(0):
            raise ValueError("Delays cannot be negative")


@dataclass(frozen=True)
class Proposal:
    # This tuple is also the proposed database uniqueness key, never a delivery receipt.
    key: tuple[str, str, str, str, str]
    action: str
    reason: str
    proposed_at: datetime


def require_timezone(value: datetime) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Timezone-aware timestamps are required")


def propose(tasks: list[Task], policy: Policy, now: datetime) -> tuple[Proposal, ...]:
    """Evaluate a call-scoped snapshot. Repeated inputs yield identical operation keys.

    The caller must authorize the scope and atomically persist keys before enqueuing.
    A policy version change permits a new proposal and requires explicit approval.
    """
    require_timezone(now)
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
        if task.kind == TaskKind.REQUIREMENTS:
            if not task.missing_requirements:
                continue
            action, reason = "human_review", "missing_requirements"
        elif task.kind == TaskKind.RESPONSE:
            if now < task.due_at + policy.response_grace:
                continue
            action, reason = "human_review", "response_window_elapsed"
        else:
            if now < task.due_at + policy.reminder_delay:
                continue
            action, reason = "simulated_reminder", task.kind.value
        key = (task.call_id, task.application_id, task.task_id, policy.version, action)
        proposals.append(Proposal(key, action, reason, now))
    return tuple(proposals)
