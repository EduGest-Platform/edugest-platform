import copy
import unittest
from dataclasses import replace
from datetime import datetime, timedelta, timezone

import numpy as np

from ml.dropout.data import FEATURES, Assessment, Attendance, Case, digest, features, generate, label, validate_splits
from ml.dropout.train import fit_baselines, matrix, predict_artifact

T = datetime(2026, 1, 25, tzinfo=timezone.utc)


def example():
    return Case("synthetic-one", "synthetic-cohort", T - timedelta(days=28), (), ("A",), (), T + timedelta(days=20))


class DatasetTests(unittest.TestCase):
    def test_seed_reproducibility_and_group_temporal_gap(self):
        data = generate(42, 90)
        self.assertEqual(digest(data), digest(generate(42, 90)))
        self.assertNotEqual(digest(data), digest(generate(43, 90)))
        validate_splits(data["rows"])
        leaked = copy.deepcopy(data["rows"])
        leaked[-1]["person_id"] = leaked[0]["person_id"]
        with self.assertRaises(ValueError):
            validate_splits(leaked)

    def test_absence_units_unknown_and_future_records(self):
        events = (Attendance("half", T, T, .5, "unjustified"), Attendance("full", T, T, 1, "unjustified"),
                  Attendance("late", T, T + timedelta(days=1), 1, "present"), Attendance("justified", T, T, 1, "justified"))
        values = features(replace(example(), attendance=events), T)
        self.assertEqual(values["unjustified_absence_days"], 1.5)
        self.assertEqual(values["justified_absence_days"], 1)
        self.assertAlmostEqual(values["attendance_unknown_fraction"], 1 / 3.5)
        self.assertIsNone(values["absence_rule_signal"])
        future = Attendance("future", T + timedelta(days=1), T, 1, "unjustified")
        self.assertEqual(values, features(replace(example(), attendance=events + (future,)), T))
        late_edit = replace(events[0], recorded_at=T + timedelta(days=1), status="present")
        self.assertEqual(values, features(replace(example(), attendance=events + (late_edit,)), T))

    def test_no_exposure_and_unpublished_or_late_assessments_are_missing(self):
        values = features(example(), T)
        self.assertIsNone(values["unjustified_absence_rate"])
        self.assertIsNone(values["mean_competency_level"])
        late = Assessment("A", T, T + timedelta(days=1), 3)
        self.assertEqual(values, features(replace(example(), assessments=(late,)), T))

    def test_label_boundaries_censoring_and_no_threshold_target(self):
        positive = replace(example(), withdrawal_at=T + timedelta(days=14), withdrawal_recorded_at=T + timedelta(days=15))
        self.assertEqual(label(positive, T), (1, "observed"))
        self.assertEqual(label(replace(positive, withdrawal_at=T), T)[1], "outside_population")
        self.assertIsNone(label(replace(example(), followup_end=T), T)[0])
        self.assertIsNone(label(replace(positive, confirmed=False), T)[0])
        self.assertEqual(label(replace(positive, attendance=(Attendance("x", T, T, 1, "present"),)), T), label(positive, T))

    def test_pipeline_json_parity_and_training_only_fit(self):
        data = generate(42, 120)
        model, fitted = fit_baselines(data)
        validation = [row for row in data["rows"] if row["split"] == "validation"]
        np.testing.assert_allclose(predict_artifact(model, validation), fitted["logistic"].predict_proba(matrix(validation))[:, 1])
        changed = copy.deepcopy(data)
        for row in changed["rows"]:
            if row["split"] != "train":
                row["features"][FEATURES[0]] = 10000
        other, _ = fit_baselines(changed)
        self.assertEqual(model["imputer_statistics"], other["imputer_statistics"])
        self.assertEqual(model["coefficients"], other["coefficients"])
        self.assertFalse(model["validated_for_people"])

    def test_feature_allowlist_and_one_class_fail_closed(self):
        data = generate(42, 90)
        data["rows"][0]["features"]["final_status"] = 1
        with self.assertRaises(ValueError):
            fit_baselines(data)
        data = generate(42, 90)
        for row in data["rows"]:
            if row["split"] == "train" and row["label"] is not None:
                row["label"] = 0
        with self.assertRaises(ValueError):
            fit_baselines(data)
