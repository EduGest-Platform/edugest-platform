"""Reproducible synthetic scenario runner, never a production evidence authenticator."""
import argparse
import csv
import hashlib
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "api"))
from metrics import Occurrence, evaluate  # noqa: E402

MAX_INPUT_BYTES = 2_000_000


def fields(value, expected, context):
    if not isinstance(value, dict) or set(value) != set(expected):
        raise ValueError(f"Invalid fields in {context}")


def synthetic_id(value):
    if not isinstance(value, str) or not re.fullmatch(r"synthetic-[a-z0-9-]{1,80}", value):
        raise ValueError("Only synthetic technical identifiers are accepted")
    return value


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON object key")
        result[key] = value
    return result


def reject_constant(_value):
    raise ValueError("Non-finite JSON constant")


def build_report(payload):
    fields(payload, {"schema_version", "synthetic_only", "scenario_id", "catalogue", "occurrences", "evidence"}, "scenario")
    if type(payload["schema_version"]) is not int or payload["schema_version"] != 1 or payload["synthetic_only"] is not True:
        raise ValueError("Version 1 and explicit synthetic_only=true are required")
    scenario_id = synthetic_id(payload["scenario_id"])
    catalogue = payload["catalogue"]
    fields(catalogue, {"version", "unit", "approval", "manual_minutes"}, "catalogue")
    synthetic_id(catalogue["version"])
    if catalogue["unit"] != "per_task_occurrence" or catalogue["approval"] != "hypothetical_not_approved":
        raise ValueError("Only explicit hypothetical per-task catalogues are supported")
    if not isinstance(catalogue["manual_minutes"], dict):
        raise ValueError("manual_minutes must be an object")
    for key in ("occurrences", "evidence"):
        if not isinstance(payload[key], list) or len(payload[key]) > 10_000:
            raise ValueError(f"Invalid {key} list")
    evidence = {}
    for item in payload["evidence"]:
        fields(item, {"id", "kind", "application_id", "task_id", "task_type"}, "evidence")
        identity = synthetic_id(item["id"])
        if identity in evidence:
            raise ValueError("Duplicate evidence identity")
        if item["kind"] != "hypothetical_completion":
            raise ValueError("Evaluations, human reviews and simulated reminders are not completion evidence")
        synthetic_id(item["application_id"])
        synthetic_id(item["task_id"])
        evidence[identity] = item
    rows, used = [], set()
    for item in payload["occurrences"]:
        fields(item, {"application_id", "task_id", "task_type", "eligible", "automated", "evidence_id"}, "occurrence")
        synthetic_id(item["application_id"])
        synthetic_id(item["task_id"])
        if item["evidence_id"] is not None:
            synthetic_id(item["evidence_id"])
        row = Occurrence(**item)
        if row.automated:
            receipt = evidence.get(row.evidence_id)
            if receipt is None or any(receipt[key] != item[key] for key in ("application_id", "task_id", "task_type")):
                raise ValueError("Completion evidence must match its application, task and type")
            used.add(row.evidence_id)
        elif row.evidence_id is not None:
            raise ValueError("Non-automated occurrences cannot claim execution evidence")
        rows.append(row)
    if used != set(evidence):
        raise ValueError("Unused completion evidence")
    metric = evaluate(rows, manual_minutes=catalogue["manual_minutes"], catalogue_version=catalogue["version"])
    return {
        "schema_version": 1, "scenario_id": scenario_id, "synthetic_only": True,
        "status": "HYPOTHETICAL_SCENARIO_NOT_MEASURED_SAVINGS", "production_evidence_authenticated": False,
        "catalogue_unit": catalogue["unit"], "catalogue_approval": catalogue["approval"],
        "metric": metric,
    }


def evaluate_file(input_path, output_dir):
    input_path, output_dir = Path(input_path), Path(output_dir)
    if input_path.stat().st_size > MAX_INPUT_BYTES:
        raise ValueError("Scenario input is too large")
    if input_path.resolve() in {(output_dir / name).resolve() for name in ("report.json", "summary.csv")}:
        raise ValueError("Output must not overwrite the input")
    raw = input_path.read_bytes()
    payload = json.loads(raw.decode("utf-8-sig"), object_pairs_hook=unique_object, parse_constant=reject_constant)
    report = build_report(payload)
    report["input_sha256"] = hashlib.sha256(raw).hexdigest()
    # Validate before creating either output. Outputs contain aggregate synthetic results only.
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "report.json").write_text(json.dumps(report, sort_keys=True, indent=2, allow_nan=False) + "\n", encoding="utf-8", newline="\n")
    csv_row = {key: value for key, value in report.items() if key != "metric"}
    csv_row.update({("metric_status" if key == "status" else key): value for key, value in report["metric"].items()})
    with (output_dir / "summary.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(csv_row), lineterminator="\n")
        writer.writeheader()
        writer.writerow({key: "undefined" if value is None else value for key, value in csv_row.items()})
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    try:
        report = evaluate_file(args.input, args.out)
    except (ValueError, TypeError, OSError):
        parser.exit(2, "Invalid scenario: check schema, hypothetical evidence, catalogue and file paths.\n")
    print(json.dumps({"scenario_id": report["scenario_id"], "status": report["status"], "input_sha256": report["input_sha256"]}))


if __name__ == "__main__":
    main()
