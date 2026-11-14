"""Train the PESTLE classifier: data loading, cleaning, and model training in one place.

All rules here were settled in ``ml/notebooks/pestle_baseline.ipynb``:

* The label is ``pestle``; rows without it are unusable for supervised training and
  are dropped (93 of 1000).
* Empty strings ``""`` are the dataset's missing-value marker, coerced to NaN.
* ``impact`` is almost always empty and ``added`` is an ingestion artifact — both
  excluded, so the model can never accidentally learn the collection process.
* Features: TF-IDF over ``title`` + one-hot (``sector``, ``topic``, ``region``,
  ``country``, ``source``) + median-imputed numerics (``intensity``,
  ``likelihood``, ``relevance``, ``pub_year``, ``pub_month``, ``span``).
* Model: LinearSVC(C=1.0) — it beat LogisticRegression and RandomForest in the
  notebook's shootout, and ``min_df=3``/``C=1.0`` were chosen by CV on the
  notebook data. The tuned pipeline is frozen here so the test set below stays
  honest: it is held out before any fitting and scored exactly once.

Usage::

    from ml.training import train

    pipeline, metrics = train()
    print(metrics["accuracy"], metrics["macro_f1"])

Run as a script (``python -m ml.training``) to print the full report.
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.impute import SimpleImputer
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
)
from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split
from sklearn.pipeline import Pipeline, make_pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.svm import LinearSVC

# Fixed seed: same data + same code -> same numbers, every run.
RANDOM_STATE = 42
TEST_SIZE = 0.2
CV_FOLDS = 5

TARGET = "pestle"
TEXT_FEATURE = "title"
CAT_FEATURES = ["sector", "topic", "region", "country", "source"]
NUM_FEATURES = ["intensity", "likelihood", "relevance", "pub_year", "pub_month", "span"]
FEATURES = [TEXT_FEATURE, *CAT_FEATURES, *NUM_FEATURES]

DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "jsondata.json"

# Saved artifacts (shared by the train_model command and ml/predict.py, so the
# path can never drift between writer and reader). The *.joblib blob is
# gitignored; metrics.json is committed for the metrics page and tests.
ARTIFACTS_DIR = Path(__file__).resolve().parents[0] / "artifacts"
MODEL_PATH = ARTIFACTS_DIR / "pestle_pipeline.joblib"
METRICS_PATH = ARTIFACTS_DIR / "metrics.json"


def load_clean_data(path: Path = DATA_PATH) -> pd.DataFrame:
    """Load ``jsondata.json`` and apply the notebook's cleaning rules.

    Returns a labelled dataframe with the model's feature columns derived and
    unlabelled rows dropped.
    """
    df = pd.DataFrame(json.loads(Path(path).read_text(encoding="utf-8")))

    # "" is the missing-value marker throughout this dataset.
    df = df.replace("", np.nan)

    # Scores arrive as strings with blanks.
    for col in ("intensity", "likelihood", "relevance", "start_year", "end_year"):
        df[col] = pd.to_numeric(df[col], errors="coerce")

    pub = pd.to_datetime(df["published"], format="mixed", errors="coerce")
    df["pub_year"] = pub.dt.year
    df["pub_month"] = pub.dt.month
    # start_year/end_year are mostly empty; compress into one nullable span.
    df["span"] = df["end_year"] - df["start_year"]

    df = df.dropna(subset=[TARGET]).reset_index(drop=True)
    df[TEXT_FEATURE] = df[TEXT_FEATURE].fillna("")
    return df


def build_pipeline() -> Pipeline:
    """The frozen notebook winner: TF-IDF + one-hot + scaled numerics -> LinearSVC.

    The vectorizer lives inside the pipeline, so in every CV fold it is fit on
    that fold's training data only — no leakage into the held-out part.
    """
    preprocessor = ColumnTransformer(
        [
            (
                "txt",
                TfidfVectorizer(ngram_range=(1, 1), min_df=3, sublinear_tf=True),
                TEXT_FEATURE,
            ),
            ("cat", OneHotEncoder(handle_unknown="ignore"), CAT_FEATURES),
            (
                "num",
                make_pipeline(SimpleImputer(strategy="median"), StandardScaler()),
                NUM_FEATURES,
            ),
        ],
        sparse_threshold=0.3,
    )
    return Pipeline(
        [
            ("preprocess", preprocessor),
            # max_iter raised purely for numerical stability (CV-identical
            # results to the default, but no convergence warnings).
            ("model", LinearSVC(C=1.0, max_iter=3000)),
        ]
    )


def train(data_path: Path = DATA_PATH) -> tuple[Pipeline, dict]:
    """Load, hold out a test set, cross-validate, fit, and score once on test.

    Returns ``(pipeline, metrics)`` where ``pipeline`` is fitted on the training
    split and ``metrics`` contains accuracy, macro-F1, the per-class report, the
    confusion matrix, and the majority-class baseline, all on the test split.
    """
    df = load_clean_data(data_path)
    X, y = df[FEATURES], df[TARGET]

    # Duplicate (and near-duplicate) titles can land on both sides of the split
    # and inflate scores. The shipped dataset has none, but a data refresh could
    # reintroduce them, so exact title copies are collapsed here and the count
    # is recorded in metrics.json where the metrics page can show it.
    n_duplicate_titles = int(X[TEXT_FEATURE].duplicated(keep="first").sum())
    if n_duplicate_titles:
        keep_idx = ~X[TEXT_FEATURE].duplicated(keep="first")
        X, y = X[keep_idx], y[keep_idx]

    # Hold out before anything is fit, so the test split never touches tuning
    # or validation (the pipeline itself is already frozen from the notebook).
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=TEST_SIZE, random_state=RANDOM_STATE, stratify=y
    )

    cv = StratifiedKFold(n_splits=CV_FOLDS, shuffle=True, random_state=RANDOM_STATE)
    cv_accuracy = cross_val_score(
        build_pipeline(), X_train, y_train, cv=cv, scoring="accuracy"
    )
    cv_macro_f1 = cross_val_score(
        build_pipeline(), X_train, y_train, cv=cv, scoring="f1_macro"
    )

    pipeline = build_pipeline().fit(X_train, y_train)
    y_pred = pipeline.predict(X_test)

    # Baseline to beat: always guess the most common class.
    baseline = DummyClassifier(strategy="most_frequent").fit(X_train, y_train)
    baseline_pred = baseline.predict(X_test)

    labels = sorted(y.unique())
    metrics = {
        "random_state": RANDOM_STATE,
        "n_rows": len(df),
        "n_duplicate_titles": n_duplicate_titles,
        "n_train": len(X_train),
        "n_test": len(X_test),
        "cv_accuracy_mean": float(cv_accuracy.mean()),
        "cv_accuracy_std": float(cv_accuracy.std()),
        "cv_macro_f1_mean": float(cv_macro_f1.mean()),
        "cv_macro_f1_std": float(cv_macro_f1.std()),
        "accuracy": float(accuracy_score(y_test, y_pred)),
        "macro_f1": float(f1_score(y_test, y_pred, average="macro")),
        "classification_report": classification_report(
            y_test, y_pred, labels=labels, digits=3, zero_division=0
        ),
        "per_class_report": classification_report(
            y_test, y_pred, labels=labels, output_dict=True, zero_division=0
        ),
        "confusion_matrix": confusion_matrix(y_test, y_pred, labels=labels).tolist(),
        "classes": labels,
        "baseline_accuracy": float(accuracy_score(y_test, baseline_pred)),
        "baseline_macro_f1": float(f1_score(y_test, baseline_pred, average="macro")),
    }
    return pipeline, metrics


if __name__ == "__main__":
    model, results = train()
    print(
        f"rows={results['n_rows']}  train={results['n_train']}  "
        f"test={results['n_test']}  (seed={results['random_state']})\n"
        f"CV (train):  acc={results['cv_accuracy_mean']:.3f}"
        f"±{results['cv_accuracy_std']:.3f}  "
        f"macroF1={results['cv_macro_f1_mean']:.3f}"
        f"±{results['cv_macro_f1_std']:.3f}\n"
        f"baseline:    acc={results['baseline_accuracy']:.3f}  "
        f"macroF1={results['baseline_macro_f1']:.3f}\n"
        f"TEST:        acc={results['accuracy']:.3f}  "
        f"macroF1={results['macro_f1']:.3f}\n"
    )
    print(results["classification_report"])
    labels = results["classes"]
    cm = pd.DataFrame(
        results["confusion_matrix"], index=labels, columns=labels
    )
    print("confusion matrix (rows=true, cols=predicted):")
    print(cm)
