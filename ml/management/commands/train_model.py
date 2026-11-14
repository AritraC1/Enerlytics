"""Retrain the PESTLE classifier and persist the artifacts.

Calls :func:`ml.training.train`, saves the fitted pipeline with joblib, and
writes a ``metrics.json`` next to it recording the training date, row counts,
class list, baseline score, and all evaluation scores.

The metrics page and tests read ``metrics.json`` directly, so it stays in git;
the ``*.joblib`` blob is gitignored (see ``.gitignore``) and rebuilt by::

    uv run python manage.py train_model
"""

import json
from datetime import datetime, timezone

from django.core.management.base import BaseCommand, CommandError
from joblib import dump

from ml.training import METRICS_PATH, MODEL_PATH, train


class Command(BaseCommand):
    help = (
        "Train the PESTLE classifier (ml/training.py), save the pipeline as a "
        "joblib artifact, and write metrics.json with the evaluation scores."
    )

    def handle(self, *args, **options):
        self.stdout.write("Training the PESTLE classifier (seed 42, 20% holdout)...")
        try:
            pipeline, metrics = train()
        except FileNotFoundError as exc:
            raise CommandError(f"Training data not found: {exc}") from exc

        # Persistence metadata on top of the training metrics. UTC so reruns on
        # different machines produce comparable timestamps.
        metrics = {
            **metrics,
            "trained_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "model_file": MODEL_PATH.name,
        }

        MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
        dump(pipeline, MODEL_PATH)
        METRICS_PATH.write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")

        self.stdout.write(
            f"rows={metrics['n_rows']}  train={metrics['n_train']}  "
            f"test={metrics['n_test']}  classes={len(metrics['classes'])}\n"
            f"baseline:    acc={metrics['baseline_accuracy']:.3f}  "
            f"macroF1={metrics['baseline_macro_f1']:.3f}\n"
            f"CV (train):  acc={metrics['cv_accuracy_mean']:.3f}"
            f"±{metrics['cv_accuracy_std']:.3f}  "
            f"macroF1={metrics['cv_macro_f1_mean']:.3f}"
            f"±{metrics['cv_macro_f1_std']:.3f}\n"
            f"TEST:        acc={metrics['accuracy']:.3f}  "
            f"macroF1={metrics['macro_f1']:.3f}"
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Saved {MODEL_PATH} and {METRICS_PATH} "
                f"(trained_at {metrics['trained_at']})"
            )
        )
