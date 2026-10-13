"""Frozen classifier and resampling utilities used by NeuroFusion-QA."""

from __future__ import annotations

import numpy as np
from numpy.typing import ArrayLike, NDArray
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import balanced_accuracy_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


C_GRID = (0.001, 0.01, 0.1, 1.0, 10.0)
THRESHOLDS = np.arange(0.05, 0.9501, 0.005)


def make_classifier(*, c: float = 1.0, seed: int = 1201) -> Pipeline:
    """Median imputation, standardization, and balanced L2 logistic regression."""
    if c not in C_GRID:
        raise ValueError(f"c must be one of the frozen values {C_GRID}")
    return Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler", StandardScaler()),
        ("classifier", LogisticRegression(
            # The default remains L2; explicit penalty is deprecated in sklearn 1.8+.
            C=c, class_weight="balanced", solver="liblinear",
            max_iter=5000, random_state=seed,
        )),
    ])


def select_balanced_threshold(y_true: ArrayLike, probabilities: ArrayLike) -> float:
    """Select the median maximizer on the frozen 0.05--0.95 threshold grid."""
    y = np.asarray(y_true, dtype=int)
    p = np.asarray(probabilities, dtype=float)
    if y.shape != p.shape or np.unique(y).size != 2 or not np.all(np.isfinite(p)):
        raise ValueError("valid binary labels and matching finite probabilities are required")
    scores = np.asarray([balanced_accuracy_score(y, p >= threshold) for threshold in THRESHOLDS])
    return float(np.median(THRESHOLDS[np.isclose(scores, np.max(scores))]))


def average_repeated_predictions(predictions: ArrayLike) -> NDArray[np.float64]:
    """Average one held-out probability per subject across outer repeats."""
    values = np.asarray(predictions, dtype=float)
    if values.ndim != 2 or not np.all(np.isfinite(values)):
        raise ValueError("predictions must be a finite repeat-by-subject array")
    if np.any((values < 0.0) | (values > 1.0)):
        raise ValueError("predictions must lie in [0, 1]")
    return np.mean(values, axis=0)

