"""Offline synthetic baseline. Artifacts are JSON, never untrusted executable pickle files."""
import argparse
import platform
from pathlib import Path

import numpy as np
import sklearn
from sklearn.dummy import DummyClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from ml.dropout.data import FEATURES, PROTOCOL, canonical, digest, generate, validate_splits


def matrix(rows):
    if any(set(row["features"]) != set(FEATURES) for row in rows):
        raise ValueError("Feature allowlist mismatch")
    result = np.array([[np.nan if row["features"][name] is None else row["features"][name] for name in FEATURES] for row in rows], dtype=float)
    if np.isinf(result).any():
        raise ValueError("Infinite features")
    return result


def fit_baselines(dataset):
    if dataset.get("synthetic_only") is not True or dataset.get("protocol") != PROTOCOL:
        raise ValueError("Only the documented synthetic protocol is supported")
    groups = validate_splits(dataset["rows"])
    training = [row for row in groups["train"] if row["label"] is not None and row["label_status"] == "observed"]
    x, y = matrix(training), np.array([row["label"] for row in training])
    if set(y) != {0, 1}:
        raise ValueError("Training requires both classes; do not fabricate metrics")
    logistic = make_pipeline(SimpleImputer(strategy="median", add_indicator=True, keep_empty_features=True),
                             StandardScaler(), LogisticRegression(max_iter=1000, random_state=dataset["seed"]))
    logistic.fit(x, y)
    dummy = DummyClassifier(strategy="prior").fit(x, y)
    imputer, scaler, estimator = logistic.steps[0][1], logistic.steps[1][1], logistic.steps[2][1]
    artifact = {"protocol": PROTOCOL, "synthetic_only": True, "validated_for_people": False, "human_review_only": True,
                "seed": dataset["seed"], "dataset_hash": digest(dataset), "training_hash": digest(training),
                "feature_names": list(FEATURES), "versions": {"python": platform.python_version(), "numpy": np.__version__, "sklearn": sklearn.__version__},
                "imputer_statistics": imputer.statistics_.tolist(), "indicator_features": imputer.indicator_.features_.tolist(),
                "scaler_mean": scaler.mean_.tolist(), "scaler_scale": scaler.scale_.tolist(),
                "coefficients": estimator.coef_[0].tolist(), "intercept": float(estimator.intercept_[0]),
                "dummy_probability": float(dummy.class_prior_[1]),
                "support": {name: {"snapshots": len(values), "observed": sum(row["label"] is not None for row in values)} for name, values in groups.items()}}
    return artifact, {"logistic": logistic, "dummy": dummy}


def predict_artifact(artifact, rows):
    if artifact.get("feature_names") != list(FEATURES) or artifact.get("synthetic_only") is not True:
        raise ValueError("Unsupported artifact")
    x = matrix(rows)
    missing = np.isnan(x)
    filled = np.where(missing, np.asarray(artifact["imputer_statistics"]), x)
    indicators = missing[:, artifact["indicator_features"]].astype(float)
    transformed = (np.concatenate([filled, indicators], axis=1) - np.asarray(artifact["scaler_mean"])) / np.asarray(artifact["scaler_scale"])
    logits = transformed @ np.asarray(artifact["coefficients"]) + artifact["intercept"]
    return 1 / (1 + np.exp(-np.clip(logits, -700, 700)))


def run(output, seed=42, people=300):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    dataset = generate(seed, people)
    artifact, _ = fit_baselines(dataset)
    (output / "dataset.json").write_text(canonical(dataset) + "\n", encoding="utf-8")
    (output / "model.json").write_text(canonical(artifact) + "\n", encoding="utf-8")
    return dataset, artifact


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Synthetic-only dropout demonstration, not valid for people")
    parser.add_argument("--out", required=True)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--people", type=int, default=300)
    args = parser.parse_args()
    dataset, model = run(args.out, args.seed, args.people)
    print(f"Synthetic snapshots: {len(dataset['rows'])}; dataset SHA256: {model['dataset_hash']}; NOT VALIDATED FOR PEOPLE")
