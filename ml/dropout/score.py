"""Batch scores for synthetic fixtures only. Observed signals are not causal explanations."""
import argparse
import json
from pathlib import Path

import numpy as np

from ml.dropout.data import FEATURES, canonical, digest
from ml.dropout.train import predict_artifact


def score_row(model, evaluation, row):
    if not row["person_id"].startswith("synthetic-person-") or not row["enrollment_id"].startswith("synthetic-person-") or not row["cohort_id"].startswith("synthetic-"):
        raise ValueError("Only synthetic fixture identifiers are accepted")
    values = row["features"]
    if set(values) != set(FEATURES) or any(value is not None and not np.isfinite(value) for value in values.values()):
        raise ValueError("Invalid feature contract")
    for name in ("attendance_unknown_fraction", "unjustified_absence_rate", "assessed_competency_fraction", "competency_missing_fraction"):
        if values[name] is not None and not 0 <= values[name] <= 1:
            raise ValueError("Fraction outside [0,1]")
    for name in ("days_since_enrollment", "scheduled_day_equivalents", "unjustified_absence_days", "justified_absence_days"):
        if values[name] is not None and values[name] < 0:
            raise ValueError("Negative exposure")
    result = {"person_id": row["person_id"], "enrollment_id": row["enrollment_id"], "cohort_id": row["cohort_id"],
              "cutoff": row["cutoff"], "model_hash": digest(model), "synthetic_only": True, "validated_for_people": False,
              "human_review_only": True, "status": "abstained", "synthetic_proxy_score": None,
              "experimental_support_signal": None, "abstention_reason": None,
              "signals": [{"feature": name, "observed_value": values[name]} for name in
                          ("unjustified_absence_days", "justified_absence_days", "attendance_unknown_fraction", "mean_competency_level")]}
    if row.get("active_at_cutoff") is not True:
        reason = "inactive_or_unknown_population"
    elif values["scheduled_day_equivalents"] is None or values["scheduled_day_equivalents"] < 3:
        reason = "insufficient_exposure_proposed_minimum"
    elif values["attendance_unknown_fraction"] is None or values["attendance_unknown_fraction"] > .5:
        reason = "insufficient_attendance_proposed_limit"
    elif evaluation["threshold"] is None:
        reason = "no_validation_threshold"
    else:
        probability = float(predict_artifact(model, [row])[0])
        if not np.isfinite(probability):
            raise ValueError("Invalid probability")
        result.update(status="scored", synthetic_proxy_score=probability,
                      experimental_support_signal=probability >= evaluation["threshold"])
        reason = None
    result["abstention_reason"] = reason
    return result


def score_dataset(dataset, model, evaluation):
    if dataset.get("synthetic_only") is not True or model.get("validated_for_people") is not False:
        raise ValueError("Not an experimental synthetic artifact")
    if digest(dataset) != model["dataset_hash"] or digest(model) != evaluation["model_hash"] or digest(dataset) != evaluation["dataset_hash"]:
        raise ValueError("Dataset/model/evaluation provenance mismatch")
    return {"synthetic_only": True, "human_review_only": True, "validated_for_people": False,
            "threshold_accepted_by_po": False, "model_hash": digest(model),
            "rows": [score_row(model, evaluation, row) for row in dataset["rows"] if row["split"] == "test"]}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Offline synthetic scoring; never generates persisted learner alerts")
    parser.add_argument("--artifacts", required=True)
    args = parser.parse_args()
    root = Path(args.artifacts)
    inputs = [json.loads((root / name).read_text(encoding="utf-8")) for name in ("dataset.json", "model.json", "evaluation.json")]
    scored = score_dataset(*inputs)
    (root / "scores.json").write_text(canonical(scored) + "\n", encoding="utf-8")
    print(f"Synthetic scored/abstained rows: {len(scored['rows'])}; HUMAN REVIEW ONLY; no database writes")
