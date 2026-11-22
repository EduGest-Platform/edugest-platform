"""Generate declared hypothetical scenarios; these are not exports of application/automation tables."""
import argparse
import json
from pathlib import Path


def scenario(mixed=False):
    occurrences, evidence = [], []
    for index in range(100):
        application_id = f"synthetic-case-{index:03d}"
        for task_type in ("documentation", "exercises"):
            task_id = f"synthetic-{task_type}-{index:03d}"
            automated = mixed and (task_type == "documentation" or index < 50)
            evidence_id = f"synthetic-completion-{task_type}-{index:03d}" if automated else None
            occurrences.append({"application_id": application_id, "task_id": task_id, "task_type": task_type,
                                "eligible": True, "automated": automated, "evidence_id": evidence_id})
            if automated:
                evidence.append({"id": evidence_id, "kind": "hypothetical_completion", "application_id": application_id,
                                 "task_id": task_id, "task_type": task_type})
    return {
        "schema_version": 1, "synthetic_only": True,
        "scenario_id": "synthetic-mixed-100" if mixed else "synthetic-manual-only-100",
        "catalogue": {"version": "synthetic-example-v1", "unit": "per_task_occurrence",
                      "approval": "hypothetical_not_approved", "manual_minutes": {"documentation": 10, "exercises": 20}},
        "occurrences": occurrences, "evidence": evidence,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    for mixed in (False, True):
        payload = scenario(mixed)
        (args.out / (payload["scenario_id"] + ".json")).write_text(
            json.dumps(payload, sort_keys=True, indent=2) + "\n", encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
