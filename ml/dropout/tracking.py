"""Local-only MLflow experiment and model registry. No remote URI or model promotion."""
import argparse
import hashlib
import json
import math
import os
import re
from contextlib import contextmanager
from pathlib import Path

from mlflow import __version__ as mlflow_version
from mlflow.exceptions import MlflowException
from mlflow.tracking import MlflowClient

from ml.dropout.data import canonical, digest

MODEL_NAME = "edugest-synthetic-dropout"
EXPERIMENT_NAME = "edugest-synthetic-only"
FILES = ("dataset.json", "model.json", "evaluation.json", "evaluation.csv", "scores.json", "model-card.md")


def local_uri(store):
    if re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", str(store)):
        raise ValueError("A local directory is required, never a remote tracking URI")
    return "sqlite:///" + (Path(store).resolve() / "tracking.sqlite").as_posix()


def close_local_client(client):
    """Release SQLite pools on Windows. Isolated adapter for the pinned MLflow 3.1.1 stores."""
    stores = [client._tracking_client.store]
    registry = getattr(client, "_registry_client_lazy", None)
    if registry is not None:
        stores.append(registry.store)
    for store in stores:
        store.engine.dispose()


@contextmanager
def local_client(store):
    uri = local_uri(store)
    client = MlflowClient(tracking_uri=uri, registry_uri=uri)
    try:
        yield client
    finally:
        close_local_client(client)


def track(artifacts, store):
    uri = local_uri(store)
    artifacts, root = Path(artifacts).resolve(), Path(store).resolve()
    payloads = {name: (artifacts / name).read_bytes() for name in FILES}
    dataset, model, evaluation, scores = [json.loads(payloads[name]) for name in ("dataset.json", "model.json", "evaluation.json", "scores.json")]
    if dataset.get("synthetic_only") is not True or model.get("validated_for_people") is not False:
        raise ValueError("Only synthetic, unvalidated artifacts may be tracked")
    if digest(dataset) != model["dataset_hash"] or digest(model) != evaluation["model_hash"] or digest(dataset) != evaluation["dataset_hash"] or digest(model) != scores["model_hash"]:
        raise ValueError("Tracking provenance mismatch")
    key = digest({name: hashlib.sha256(content).hexdigest() for name, content in payloads.items()})
    root.mkdir(parents=True, exist_ok=True)
    lock = root / "tracking.lock"
    try:
        descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError as exc:
        raise RuntimeError("Local writer or stale tracking.lock exists; inspect before retrying") from exc
    os.close(descriptor)
    client, run_id = None, None
    try:
        client = MlflowClient(tracking_uri=uri, registry_uri=uri)
        experiment = client.get_experiment_by_name(EXPERIMENT_NAME)
        experiment_id = experiment.experiment_id if experiment else client.create_experiment(
            EXPERIMENT_NAME, artifact_location=(root / "artifacts").as_uri())
        matches = client.search_runs([experiment_id], filter_string=f"tags.reproducibility_key = '{key}'", max_results=100)
        for existing in matches:
            version = existing.data.tags.get("registered_version")
            if existing.info.status == "FINISHED" and version:
                client.get_model_version(MODEL_NAME, version)  # do not reuse a missing registry receipt
                return {"run_id": existing.info.run_id, "registered_model": MODEL_NAME, "registered_version": version,
                        "reused": True, "synthetic_only": True, "promoted": False}
        run = client.create_run(experiment_id, tags={"reproducibility_key": key, "synthetic_only": "true", "validated_for_people": "false",
                                                     "human_review_only": "true", "acceptance": "pending", "mlflow_version": mlflow_version})
        run_id = run.info.run_id
        for name, value in {"seed": model["seed"], "protocol": model["protocol"], "dataset_hash": model["dataset_hash"], "model_hash": digest(model),
                            "validation_hash": evaluation["validation_hash"], "feature_count": len(model["feature_names"])}.items():
            client.log_param(run_id, name, str(value))
        for row in evaluation["results"]:
            for metric in ("n", "positives", "coverage", "precision", "recall", "f1", "pr_auc", "brier", "alert_fraction"):
                if row[metric] is not None:
                    if not math.isfinite(row[metric]):
                        raise ValueError("Nonfinite metrics cannot be tracked")
                    client.log_metric(run_id, f"{row['split']}.{row['model']}.{metric}", float(row[metric]))
        report_staging = root / "staging" / key / "reports"
        report_staging.mkdir(parents=True, exist_ok=True)
        for name, content in payloads.items():
            (report_staging / name).write_bytes(content)
            client.log_artifact(run_id, str(report_staging / name), artifact_path="reports")
        staging = root / "staging" / key
        staging.mkdir(parents=True, exist_ok=True)
        (staging / "model.json").write_bytes(payloads["model.json"])
        # MLmodel is YAML; JSON is a YAML subset. This is a custom JSON flavor, not a serving/pyfunc model.
        flavor = {"flavors": {"edugest_synthetic_json": {"model_file": "model.json", "loader_function": "ml.dropout.train.predict_artifact"}},
                  "metadata": {"synthetic_only": True, "validated_for_people": False, "acceptance": "pending"}}
        (staging / "MLmodel").write_text(canonical(flavor), encoding="utf-8")
        client.log_artifact(run_id, str(staging / "model.json"), artifact_path="model")
        client.log_artifact(run_id, str(staging / "MLmodel"), artifact_path="model")
        try:
            client.get_registered_model(MODEL_NAME)
        except MlflowException as exc:
            if exc.error_code != "RESOURCE_DOES_NOT_EXIST":
                raise
            client.create_registered_model(MODEL_NAME, tags={"synthetic_only": "true", "acceptance": "pending"})
        # Explicit local artifact URI avoids implicit global tracking-URI resolution in the SDK.
        version = client.create_model_version(MODEL_NAME, source=run.info.artifact_uri.rstrip("/") + "/model", run_id=run_id,
                                              tags={"synthetic_only": "true", "validated_for_people": "false", "acceptance": "pending"})
        client.set_tag(run_id, "registered_version", str(version.version))
        client.set_terminated(run_id, status="FINISHED")
        return {"run_id": run_id, "registered_model": MODEL_NAME, "registered_version": str(version.version),
                "reused": False, "synthetic_only": True, "promoted": False}
    except Exception:
        if client is not None and run_id is not None:
            client.set_terminated(run_id, status="FAILED")
        raise
    finally:
        try:
            if client is not None:
                close_local_client(client)
        finally:
            lock.unlink()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Local SQLite tracking and unpromoted synthetic JSON model registry")
    parser.add_argument("--artifacts", required=True)
    parser.add_argument("--store", required=True)
    args = parser.parse_args()
    print(canonical(track(args.artifacts, args.store)))
