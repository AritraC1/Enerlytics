"""Tests for the ML data preparation and prediction API.

The goal is that retraining or changing features cannot silently break the
Predict page: the cleaning rules keep dropping unlabelled rows, predict()
keeps its documented result shape, and a missing model file degrades to a
friendly "not trained" message instead of a 500.
"""

import json
import tempfile
import unittest.mock
from pathlib import Path

import numpy as np
from django.test import TestCase

from ml import predict as predict_module
from ml.predict import TOP_N, predict_pestle
from ml.training import TARGET, load_clean_data, train

# Minimal row with every column load_clean_data() derives from. Numeric
# scores arrive as strings (the dataset's real shape); start/end year blanks
# exercise the missing-value path.
_FULL_ROW = {
    "title": "Solar costs fall across oil and gas markets",
    "sector": "Energy",
    "topic": "Solar",
    "region": "World",
    "country": "India",
    "source": "News",
    "pestle": "Technological",
    "published": "2024-01-15",
    "start_year": "",
    "end_year": "",
    "intensity": "12.5",
    "likelihood": "3.0",
    "relevance": "4.0",
}


def _write_json(rows) -> Path:
    path = Path(tempfile.mkdtemp()) / "jsondata.json"
    path.write_text(json.dumps(rows), encoding="utf-8")
    return path


class DataPreparationTests(TestCase):
    """The notebook's cleaning rules, frozen as tests."""

    def test_drops_rows_with_no_pestle_value(self):
        """Rows with an empty PESTLE ("" — the dataset's missing marker) are
        unusable for supervised training and must be dropped, leaving only
        fully labelled rows."""
        path = _write_json(
            [
                _FULL_ROW,  # labelled: kept
                {**_FULL_ROW, "title": "Oil prices surge", "pestle": ""},  # dropped
            ]
        )
        df = load_clean_data(path)
        self.assertEqual(len(df), 1)
        self.assertTrue(df[TARGET].notna().all())
        self.assertEqual(df["title"].iloc[0], _FULL_ROW["title"])

    def test_train_collapses_duplicate_titles(self):
        """Exact duplicate titles must not land on both sides of the train/test
        split, where memorising the copy would inflate the score. train()
        collapses them and reports the count in metrics.json."""
        # 20 unique rows, each duplicated exactly once -> 20 collapsed copies.
        rows = []
        for i in range(20):
            row = {
                **_FULL_ROW,
                "title": f"Unique energy headline number {i}",
                "sector": "Energy" if i % 2 == 0 else "Manufacturing",
                "pestle": "Economic" if i % 2 == 0 else "Technological",
            }
            rows.append(row)
            rows.append({**row, "source": "Copy"})  # exact-title duplicate
        self.assertEqual(len(rows), 40)

        pipeline, metrics = train(_write_json(rows))
        self.assertEqual(metrics["n_duplicate_titles"], 20)
        # The split only ever sees unique rows.
        self.assertEqual(metrics["n_train"] + metrics["n_test"], 20)


class _FakePipeline:
    """Stands in for the saved LinearSVC pipeline: fixed scores, no sklearn."""

    classes_ = np.array(["Economic", "Political", "Technological"])

    def decision_function(self, X):
        # One row: highest raw score for "Technological" (index 2).
        return np.array([[0.0, 1.0, 2.0]])


class PredictTests(TestCase):
    def setUp(self):
        # Bypass the artifact file entirely: swap in the fake pipeline and
        # restore the real cache afterwards.
        patcher = unittest.mock.patch.object(predict_module, "_model", _FakePipeline())
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_returns_expected_structure(self):
        result = predict_pestle("Solar costs fall across oil and gas markets")
        self.assertTrue(result["available"])
        self.assertIsNone(result["error"])
        self.assertEqual(result["label"], "Technological")
        self.assertIsInstance(result["probability"], float)

        # Top-N entries, best first, every confidence within [0, 1].
        self.assertEqual(len(result["top"]), TOP_N)
        self.assertEqual(
            [entry["label"] for entry in result["top"]],
            ["Technological", "Political", "Economic"],
        )
        self.assertTrue(
            all(0.0 <= entry["probability"] <= 1.0 for entry in result["top"])
        )
        probabilities = [entry["probability"] for entry in result["top"]]
        self.assertAlmostEqual(sum(probabilities), 1.0, places=3)
        self.assertEqual(result["top"][0]["probability"], result["probability"])

    def test_too_short_input_refused(self):
        result = predict_pestle("ab")
        self.assertFalse(result["available"])
        self.assertIn("too short", result["error"].lower())


class NoModelTests(TestCase):
    def test_missing_model_file_returns_friendly_result(self):
        """With no artifact on disk (and nothing cached), predict() degrades
        to an "available: False" result with the train command hint — it must
        not raise, so the Predict page can show the message instead of a 500."""
        missing = Path(tempfile.gettempdir()) / "definitely-not-a-model.joblib"
        with unittest.mock.patch.object(predict_module, "_model", None), \
             unittest.mock.patch.object(predict_module, "_load_failed", False), \
             unittest.mock.patch.object(predict_module, "MODEL_PATH", missing):
            result = predict_pestle("Oil prices surge as supply concerns mount")
        self.assertFalse(result["available"])
        self.assertIsNone(result["label"])
        self.assertIn("Model not trained yet", result["error"])
        self.assertIn("train_model", result["error"])
