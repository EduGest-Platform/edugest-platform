"""Offline occurrence coverage. Inputs must come from an approved task inventory.

Never use generated proposals as evidence of completed automation.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Occurrence:
    application_id: str
    task_id: str
    eligible: bool
    automated: bool
    evidence_id: str | None = None


def evaluate(rows: list[Occurrence], *, formula_approved: bool = False) -> dict:
    identities = [(row.application_id, row.task_id) for row in rows]
    if len(set(identities)) != len(rows):
        raise ValueError("Duplicate task occurrence")
    for row in rows:
        if not row.application_id.strip() or not row.task_id.strip():
            raise ValueError("Occurrence identifiers are required")
        if row.automated and (not row.eligible or not row.evidence_id or not row.evidence_id.strip()):
            raise ValueError("Automated occurrences must be eligible and have execution evidence")
    denominator = sum(row.eligible for row in rows)
    numerator = sum(row.automated for row in rows)
    case_count = len({row.application_id for row in rows})
    return {
        "unit": "eligible_task_occurrence",
        "numerator": numerator,
        "denominator": denominator,
        "percentage": 100 * numerator / denominator if denominator else None,
        "case_count": case_count,
        "formula_approved": formula_approved,
        "minimum_case_count_met": case_count >= 100,
        "status": "OFFLINE_INPUTS_NOT_INDEPENDENTLY_VERIFIED",
    }
