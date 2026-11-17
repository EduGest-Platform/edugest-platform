"""Estimated manual time saved; evidence authenticity needs independent verification."""

from dataclasses import dataclass
from math import isfinite
from numbers import Real

from app.modules.automation.engine import TaskKind


# Explicit scope, not catalogue membership: minutes never authorize a new task type.
PRESELECTION_TASK_TYPES = frozenset({
    TaskKind.INFORMATION_SESSION.value,
    TaskKind.EXERCISES.value,
    TaskKind.DOCUMENTATION.value,
    TaskKind.REQUIREMENTS.value,
    TaskKind.RESPONSE.value,
})


def identifier(value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError('Identifiers must be non-empty strings')
    return value.strip()


@dataclass(frozen=True)
class Occurrence:
    application_id: str
    task_id: str
    task_type: str
    eligible: bool
    automated: bool
    evidence_id: str | None = None

    def __post_init__(self):
        for name in ('application_id', 'task_id', 'task_type'):
            object.__setattr__(self, name, identifier(getattr(self, name)))
        if type(self.eligible) is not bool or type(self.automated) is not bool:
            raise ValueError('Eligibility and automation flags must be booleans')
        if self.evidence_id is not None:
            object.__setattr__(self, 'evidence_id', identifier(self.evidence_id))
        if self.automated and (not self.eligible or self.evidence_id is None):
            raise ValueError('Automated occurrences require eligibility and execution evidence')
        if self.eligible and self.task_type not in PRESELECTION_TASK_TYPES:
            raise ValueError('Eligible task type must be an allowed preselection TaskKind')


def evaluate(rows: list[Occurrence], *, manual_minutes: dict[str, float], catalogue_version: str) -> dict:
    catalogue_version = identifier(catalogue_version)
    minutes = {}
    for name, value in manual_minutes.items():
        name = identifier(name)
        if name in minutes:
            raise ValueError('Duplicate normalized catalogue task type')
        if isinstance(value, bool) or not isinstance(value, Real) or not isfinite(value) or value < 0:
            raise ValueError('Manual minutes must be finite, nonnegative numbers')
        minutes[name] = float(value)
    identities = [(row.application_id, row.task_id) for row in rows]
    if len(set(identities)) != len(rows):
        raise ValueError('Duplicate task occurrence')
    evidence = [row.evidence_id for row in rows if row.automated]
    if len(set(evidence)) != len(evidence):
        raise ValueError('Each automated occurrence requires unique execution evidence')
    eligible = [row for row in rows if row.eligible]
    if any(row.task_type not in minutes for row in eligible):
        raise ValueError('Missing manual minutes for eligible task type')
    automated = [row for row in eligible if row.automated]
    baseline = sum(minutes[row.task_type] for row in eligible)
    saved = sum(minutes[row.task_type] for row in automated)
    if not isfinite(baseline) or not isfinite(saved):
        raise ValueError('Time totals must be finite')
    eligible_cases = len({row.application_id for row in eligible})
    return {
        'unit': 'estimated_manual_minutes_saved',
        'catalogue_version': catalogue_version,
        'eligible_task_count': len(eligible),
        'automated_task_count': len(automated),
        'baseline_manual_minutes': baseline,
        'estimated_saved_minutes': saved,
        'percentage': 100 * (saved / baseline) if baseline else None,
        'case_count': len({row.application_id for row in rows}),
        'eligible_case_count': eligible_cases,
        'minimum_case_count_met': eligible_cases >= 100,
        'po_time_saved_definition_confirmed_on': '2026-11-17',
        'client_approval': 'PENDING',
        'status': 'ESTIMATED_UNDER_CATALOGUE_ASSUMPTIONS_NOT_PRODUCTION_SAVINGS',
    }
