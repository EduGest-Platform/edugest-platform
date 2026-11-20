import copy
import unittest

import numpy as np

from ml.dropout.data import generate
from ml.dropout.evaluate import evaluate_dataset, metrics, select_threshold
from ml.dropout.train import fit_baselines


class EvaluationTests(unittest.TestCase):
    def test_confusion_and_calibration_known_values(self):
        result = metrics([0, 0, 1, 1], [.1, .8, .2, .9], .5)
        self.assertEqual(result["confusion"], {"tn": 1, "fp": 1, "fn": 1, "tp": 1})
        self.assertEqual(result["f1"], .5)
        self.assertEqual(sum(item["n"] for item in result["calibration"]), 4)
        self.assertAlmostEqual(result["brier"], (.01 + .64 + .64 + .01) / 4)

    def test_undefined_and_one_class_are_explicit(self):
        self.assertIsNone(metrics([], [], .5)["brier"])
        result = metrics([0, 0], [.1, .2], .5)
        self.assertIsNone(result["recall"])
        self.assertIsNone(result["precision"])
        self.assertIsNone(result["pr_auc"])
        self.assertIsNone(select_threshold([0, 0], [.1, .2]))
        with self.assertRaises(ValueError):
            metrics([0], [float("nan")], .5)

    def test_threshold_capacity_and_no_test_label_tuning(self):
        y, p = [0, 1, 0, 1], np.array([.1, .8, .3, .9])
        threshold = select_threshold(y, p, .25)
        self.assertLessEqual(float((p >= threshold).mean()), .25)
        data = generate(42, 120)
        model, _ = fit_baselines(data)
        first = evaluate_dataset(data, model)
        modified = copy.deepcopy(data)
        for row in modified["rows"]:
            if row["split"] == "test" and row["label"] is not None:
                row["label"] = 1 - row["label"]
        other, _ = fit_baselines(modified)
        second = evaluate_dataset(modified, other)
        self.assertEqual(first["threshold"], second["threshold"])
        self.assertEqual(first["validation_hash"], second["validation_hash"])
        self.assertEqual(len(first["results"]), 6)
        self.assertFalse(first["validated_for_people"])
        with self.assertRaises(ValueError):
            evaluate_dataset(modified, model)
