"""Reproducible synthetic-only validation/test metrics, threshold provenance and evaluation table."""
import argparse
import csv
import json
from pathlib import Path

import numpy as np
from sklearn.metrics import average_precision_score, brier_score_loss, confusion_matrix

from ml.dropout.data import FEATURES, canonical, digest, validate_splits
from ml.dropout.train import predict_artifact


def metrics(y, probabilities, threshold):
    y, probabilities = np.asarray(y, dtype=int), np.asarray(probabilities, dtype=float)
    if len(y) != len(probabilities) or not np.isin(y, [0, 1]).all() or not np.isfinite(probabilities).all() or ((probabilities < 0) | (probabilities > 1)).any():
        raise ValueError("Invalid binary evaluation")
    if not len(y):
        return {"n": 0, "positives": 0, "prevalence": None, "confusion": None, "precision": None,
                "recall": None, "f1": None, "pr_auc": None, "brier": None, "calibration": [], "alert_fraction": None}
    prediction = probabilities >= threshold
    tn, fp, fn, tp = (int(v) for v in confusion_matrix(y, prediction, labels=[0, 1]).ravel())
    bins = []
    for lower, upper in zip(np.linspace(0, 1, 11)[:-1], np.linspace(0, 1, 11)[1:]):
        selected = (probabilities >= lower) & ((probabilities < upper) if upper < 1 else (probabilities <= upper))
        bins.append({"lower": float(lower), "upper": float(upper), "n": int(selected.sum()),
                     "mean_probability": float(probabilities[selected].mean()) if selected.any() else None,
                     "positive_fraction": float(y[selected].mean()) if selected.any() else None})
    return {"n": len(y), "positives": int(y.sum()), "prevalence": float(y.mean()), "confusion": {"tn": tn, "fp": fp, "fn": fn, "tp": tp},
            "precision": tp / (tp + fp) if tp + fp else None, "recall": tp / (tp + fn) if tp + fn else None,
            "f1": 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else None,
            "pr_auc": float(average_precision_score(y, probabilities)) if len(set(y)) == 2 else None,
            "brier": float(brier_score_loss(y, probabilities)), "calibration": bins, "alert_fraction": float(prediction.mean())}


def select_threshold(y, probabilities, capacity=.25):
    """Experimental review capacity, not an accepted PO support policy or a dropout decision."""
    if not 0 < capacity <= 1:
        raise ValueError("Capacity must be in (0,1]")
    if set(y) != {0, 1}:
        return None
    candidates = []
    for threshold in sorted(set(float(p) for p in probabilities) | {1.000001}):
        result = metrics(y, probabilities, threshold)
        if result["alert_fraction"] <= capacity:
            candidates.append((result["f1"] or 0, threshold))
    return max(candidates)[1] if candidates else None


def evaluate_dataset(dataset, model, capacity=.25):
    if digest(dataset) != model["dataset_hash"]:
        raise ValueError("Dataset/artifact provenance mismatch")
    groups = validate_splits(dataset["rows"])
    observed = {name: [row for row in rows if row["label"] is not None and row["label_status"] == "observed"] for name, rows in groups.items()}
    validation = observed["validation"]
    validation_scores = predict_artifact(model, validation) if validation else np.array([])
    threshold = select_threshold([row["label"] for row in validation], validation_scores, capacity)
    report = {"synthetic_only": True, "validated_for_people": False, "dataset_hash": digest(dataset), "model_hash": digest(model),
              "threshold_selected_on": "validation", "validation_hash": digest(validation), "threshold": threshold,
              "capacity_proposal": capacity, "threshold_accepted_by_po": False, "results": [], "missingness": {}}
    for split in ("validation", "test"):
        rows = observed[split]
        y = [row["label"] for row in rows]
        scores = predict_artifact(model, rows) if rows else np.array([])
        report["missingness"][split] = {feature: sum(row["features"][feature] is None for row in rows) / len(rows) if rows else None for feature in FEATURES}
        for name, probabilities in (("logistic", scores), ("dummy", np.full(len(rows), model["dummy_probability"]))):
            result = metrics(y, probabilities, threshold if threshold is not None else .5)
            report["results"].append({"model": name, "split": split, "coverage": 1.0 if rows else 0.0,
                                       "classification_threshold": threshold if threshold is not None else .5,
                                       "threshold_status": "validation_selected" if threshold is not None else "fallback_for_diagnostics_only",
                                       **result})
        covered = [row for row in rows if row["features"]["absence_rule_signal"] is not None]
        heuristic = metrics([row["label"] for row in covered], [row["features"]["absence_rule_signal"] for row in covered], .5)
        heuristic.update(brier=None, pr_auc=None, calibration=[])
        report["results"].append({"model": "session_rule", "split": split, "coverage": len(covered) / len(rows) if rows else 0.0,
                                   "classification_threshold": None, "threshold_status": "illustrative_not_probabilistic", **heuristic})
    return report


def write_report(directory, report):
    directory = Path(directory)
    (directory / "evaluation.json").write_text(canonical(report) + "\n", encoding="utf-8")
    fields = ["model", "split", "n", "positives", "coverage", "prevalence", "precision", "recall", "f1", "pr_auc", "brier", "alert_fraction"]
    with (directory / "evaluation.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows({field: result[field] for field in fields} for result in report["results"])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Synthetic validation only: metrics do not establish predictive validity")
    parser.add_argument("--artifacts", required=True)
    args = parser.parse_args()
    directory = Path(args.artifacts)
    dataset = json.loads((directory / "dataset.json").read_text(encoding="utf-8"))
    model = json.loads((directory / "model.json").read_text(encoding="utf-8"))
    result = evaluate_dataset(dataset, model)
    write_report(directory, result)
    print(f"Evaluation table: {len(result['results'])} rows; threshold selected on validation only; SYNTHETIC / NOT VALIDATED FOR PEOPLE")
