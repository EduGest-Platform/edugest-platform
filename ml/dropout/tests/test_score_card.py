import copy
import unittest

from ml.dropout.data import canonical, generate
from ml.dropout.evaluate import evaluate_dataset
from ml.dropout.model_card import render_card
from ml.dropout.score import score_dataset, score_row
from ml.dropout.train import fit_baselines


class ScoringTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dataset = generate(42, 180)
        cls.model, _ = fit_baselines(cls.dataset)
        cls.evaluation = evaluate_dataset(cls.dataset, cls.model)

    def test_reproducible_batch_and_no_actions(self):
        first = score_dataset(self.dataset, self.model, self.evaluation)
        self.assertEqual(canonical(first), canonical(score_dataset(self.dataset, self.model, self.evaluation)))
        self.assertTrue(first["human_review_only"])
        self.assertFalse(first["validated_for_people"])
        for row in first["rows"]:
            self.assertNotIn("label", row)
            self.assertNotIn("admission", row)
            if row["status"] == "scored":
                self.assertTrue(0 <= row["synthetic_proxy_score"] <= 1)

    def test_abstention_is_not_low_risk(self):
        row = copy.deepcopy(self.dataset["rows"][0])
        row["active_at_cutoff"] = False
        result = score_row(self.model, self.evaluation, row)
        self.assertIsNone(result["synthetic_proxy_score"])
        self.assertEqual(result["status"], "abstained")
        row["active_at_cutoff"] = True
        row["features"]["scheduled_day_equivalents"] = 0
        self.assertEqual(score_row(self.model, self.evaluation, row)["status"], "abstained")
        row["features"]["scheduled_day_equivalents"] = 10
        row["features"]["attendance_unknown_fraction"] = .9
        self.assertEqual(score_row(self.model, self.evaluation, row)["status"], "abstained")
        row["features"]["attendance_unknown_fraction"] = .1
        missing_threshold = {**self.evaluation, "threshold": None}
        self.assertEqual(score_row(self.model, missing_threshold, row)["abstention_reason"], "no_validation_threshold")

    def test_provenance_and_real_identifiers_fail(self):
        changed = copy.deepcopy(self.model)
        changed["intercept"] += 1
        with self.assertRaises(ValueError):
            score_dataset(self.dataset, changed, self.evaluation)
        row = copy.deepcopy(self.dataset["rows"][0])
        row["person_id"] = "real-person"
        with self.assertRaises(ValueError):
            score_row(self.model, self.evaluation, row)

    def test_card_is_bound_to_actual_artifacts_and_bilingual(self):
        card = render_card(self.dataset, self.model, self.evaluation)
        self.assertIn(self.model["dataset_hash"], card)
        self.assertIn("NO VALIDADO PARA PERSONAS", card)
        self.assertIn("NOT VALIDATED FOR PEOPLE", card)
        self.assertEqual(card, render_card(self.dataset, self.model, self.evaluation))
        changed = copy.deepcopy(self.dataset)
        changed["seed"] = 999
        with self.assertRaises(ValueError):
            render_card(changed, self.model, self.evaluation)
