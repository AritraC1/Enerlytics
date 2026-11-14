"""Prediction API for the dashboard.

The dashboard calls :func:`predict_pestle` with the insight's ``title`` text
(the field the model was trained on) and gets a plain dict back. It never
touches scikit-learn, and the page never crashes: a missing model or a
too-short input yields a result dict with an ``error`` message instead of an
exception.

The saved model is a LinearSVC, which has no ``predict_proba``; confidences
are therefore softmax-normalized ``decision_function`` scores. Treat them as
relative confidence between classes, not calibrated probabilities.

Usage::

    from ml.predict import predict_pestle

    result = predict_pestle("Solar costs fall across oil and gas markets")
    if result["available"]:
        print(result["label"], result["top"])
"""

import numpy as np
import pandas as pd
from joblib import load

from ml.training import CAT_FEATURES, MODEL_PATH, NUM_FEATURES

# Below this many characters a title carries no usable signal (TF-IDF words
# need at least a token or two), so we refuse instead of guessing.
MIN_TEXT_CHARS = 3
TOP_N = 3

# Loaded lazily on first successful use, then cached for the process lifetime.
_model = None
_load_failed = False


def _get_model():
    """Return the cached pipeline, or ``None`` while no usable model exists.

    While the file is missing we only pay one ``is_file()`` stat per call, so a
    model trained mid-flight (e.g. via ``manage.py train_model``) is picked up
    without a server restart. A failed load (corrupt/incompatible artifact) is
    remembered and never retried in-process.
    """
    global _model, _load_failed
    if _model is not None:
        return _model
    if _load_failed:
        return None
    if MODEL_PATH.is_file():
        try:
            _model = load(MODEL_PATH)
        except Exception:
            _load_failed = True
    return _model


def _result(message=None, label=None, probability=None, top=None):
    """One stable result shape, valid whether or not a prediction happened."""
    return {
        "available": message is None,
        "label": label,
        "probability": probability,
        "top": top or [],
        "error": message,
    }


def predict_pestle(text: str) -> dict:
    """Predict the PESTLE label for one insight title.

    Returns a dict with:

    * ``available`` — False when the model is missing or the input is unusable.
    * ``label`` / ``probability`` — the top prediction and its confidence.
    * ``top`` — the top three ``{"label", "probability"}`` entries.
    * ``error`` — a human-readable message, or None.
    """
    text = str(text or "").strip()
    if len(text) < MIN_TEXT_CHARS:
        return _result(
            f"Input too short: give at least {MIN_TEXT_CHARS} characters of the insight title."
        )

    model = _get_model()
    if model is None:
        return _result("Model not trained yet. Run: uv run python manage.py train_model")

    # One-row frame with the model's feature columns. Categorical fields get
    # "" (unknown to the fitted encoder -> neutral all-zero one-hot row) and
    # numeric fields get NaN so the fitted median imputers supply training-set
    # medians — i.e. "no evidence" defaults for everything but the title.
    row = pd.DataFrame(
        [
            {
                "title": text,
                **{column: "" for column in CAT_FEATURES},
                **{column: np.nan for column in NUM_FEATURES},
            }
        ]
    )

    scores = np.asarray(model.decision_function(row))[0]
    confidence = np.exp(scores - scores.max())
    confidence /= confidence.sum()

    order = confidence.argsort()[::-1][:TOP_N]
    classes = list(model.classes_)
    top = [
        {"label": classes[i], "probability": round(float(confidence[i]), 4)}
        for i in order
    ]
    return _result(
        label=top[0]["label"],
        probability=top[0]["probability"],
        top=top,
    )


if __name__ == "__main__":
    samples = [
        "Oil prices surge as supply concerns mount",
        "New solar panel efficiency record announced",
        "New labour law passes parliament",
        "",
    ]
    for sample in samples:
        result = predict_pestle(sample)
        print(f"{sample!r:50} -> {result}")
