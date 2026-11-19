import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from mlflow.artifacts import download_artifacts

from ml.dropout.data import canonical
from ml.dropout.evaluate import evaluate_dataset, write_report
from ml.dropout.model_card import render_card
from ml.dropout.score import score_dataset
from ml.dropout.tracking import EXPERIMENT_NAME, MODEL_NAME, local_client, local_uri, track
from ml.dropout.train import run


class TrackingTests(unittest.TestCase):
    def test_real_local_tracking_registry_and_reuse_without_promotion(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            artifacts, store = root / "artifacts", root / "local-store"
            dataset, model = run(artifacts, people=120)
            report = evaluate_dataset(dataset, model)
            write_report(artifacts, report)
            (artifacts / "scores.json").write_text(canonical(score_dataset(dataset, model, report)), encoding="utf-8")
            (artifacts / "model-card.md").write_text(render_card(dataset, model, report), encoding="utf-8")
            first = track(artifacts, store)
            second = track(artifacts, store)
            self.assertFalse(first["reused"])
            self.assertTrue(second["reused"])
            self.assertEqual(first["run_id"], second["run_id"])
            self.assertEqual(first["registered_version"], second["registered_version"])
            with local_client(store) as client:
                experiment = client.get_experiment_by_name(EXPERIMENT_NAME)
                self.assertEqual(len(client.search_runs([experiment.experiment_id])), 1)
                version = client.get_model_version(MODEL_NAME, first["registered_version"])
                self.assertIn(version.current_stage, (None, "None"))
                self.assertEqual(version.tags["validated_for_people"], "false")
                tracked = client.get_run(first["run_id"])
                self.assertIn("test.logistic.brier", tracked.data.metrics)
                self.assertEqual(tracked.data.params["dataset_hash"], model["dataset_hash"])
                self.assertTrue(version.source.startswith("file:"))
                downloaded = download_artifacts(artifact_uri=version.source + "/model.json", dst_path=str(root))
                self.assertEqual(json.loads(Path(downloaded).read_text())["dataset_hash"], model["dataset_hash"])
            self.assertFalse((store / "tracking.lock").exists())
            (store / "tracking.lock").write_text("synthetic test writer", encoding="utf-8")
            with self.assertRaises(RuntimeError):
                track(artifacts, store)
            (store / "tracking.lock").unlink()
            card = (artifacts / "model-card.md").read_text(encoding="utf-8")
            (artifacts / "model-card.md").write_text(card + "\nSynthetic failure probe", encoding="utf-8")
            with patch("ml.dropout.tracking.MlflowClient.log_metric", side_effect=RuntimeError("Synthetic logging failure")):
                with self.assertRaises(RuntimeError):
                    track(artifacts, store)
            self.assertFalse((store / "tracking.lock").exists())
            with local_client(store) as client:
                statuses = {run.info.status for run in client.search_runs([experiment.experiment_id])}
                self.assertEqual(statuses, {"FINISHED", "FAILED"})
                self.assertEqual(len(client.search_model_versions(f"name = '{MODEL_NAME}'")), 1)
            (artifacts / "model-card.md").write_text(card, encoding="utf-8")
            self.assertTrue(track(artifacts, store)["reused"])
            changed = json.loads((artifacts / "model.json").read_text())
            changed["seed"] = 999
            (artifacts / "model.json").write_text(canonical(changed), encoding="utf-8")
            with self.assertRaises(ValueError):
                track(artifacts, store)

    def test_remote_tracking_is_rejected(self):
        for remote in ("https://example.test", "http://localhost:5000", "sqlite:///outside.db", "databricks://workspace"):
            with self.assertRaises(ValueError):
                local_uri(remote)
