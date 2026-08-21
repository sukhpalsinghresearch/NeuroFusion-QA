"""Subject-level metrics and paired uncertainty for frozen comparisons."""

from __future__ import annotations

from collections.abc import Callable

import numpy as np
from numpy.typing import ArrayLike, NDArray
from sklearn.metrics import average_precision_score, brier_score_loss, log_loss, roc_auc_score
from scipy.stats import spearmanr


def prediction_profile(y_true: ArrayLike, probabilities: ArrayLike) -> dict[str, float]:
    """Compute the four aggregate metrics reported in the manuscript."""
    y = np.asarray(y_true, dtype=int)
    p = np.clip(np.asarray(probabilities, dtype=float), 1e-6, 1.0 - 1e-6)
    return {
        "roc_auc": float(roc_auc_score(y, p)),
        "average_precision": float(average_precision_score(y, p)),
        "brier_score": float(brier_score_loss(y, p)),
        "log_loss": float(log_loss(y, p, labels=[0, 1])),
    }


def paired_subject_bootstrap(
    y_true: ArrayLike,
    reference: ArrayLike,
    candidate: ArrayLike,
    metric: Callable[[NDArray[np.int_], NDArray[np.float64]], float],
    *,
    n_resamples: int = 5000,
    seed: int = 20260816,
) -> dict[str, float]:
    """Bootstrap candidate-minus-reference differences using matched subjects."""
    y = np.asarray(y_true, dtype=int)
    ref = np.asarray(reference, dtype=float)
    cand = np.asarray(candidate, dtype=float)
    if not (y.shape == ref.shape == cand.shape):
        raise ValueError("all subject-level arrays must have the same shape")
    rng = np.random.default_rng(seed)
    differences: list[float] = []
    for _ in range(n_resamples):
        indices = rng.integers(0, y.size, size=y.size)
        if np.unique(y[indices]).size < 2:
            continue
        differences.append(metric(y[indices], cand[indices]) - metric(y[indices], ref[indices]))
    values = np.asarray(differences, dtype=float)
    if values.size == 0:
        raise ValueError("no valid bootstrap samples")
    return {
        "difference": float(metric(y, cand) - metric(y, ref)),
        "ci_low": float(np.quantile(values, 0.025)),
        "ci_high": float(np.quantile(values, 0.975)),
        "valid_resamples": int(values.size),
    }


def gate_validity(
    binary_utility: ArrayLike,
    continuous_utility: ArrayLike,
    fmri_weight: ArrayLike,
    *,
    n_resamples: int = 5000,
    seed: int = 20260816,
) -> dict[str, float]:
    """Evaluate whether an fMRI weight tracks held-out fMRI utility."""
    binary = np.asarray(binary_utility, dtype=int)
    continuous = np.asarray(continuous_utility, dtype=float)
    weight = np.asarray(fmri_weight, dtype=float)
    if not (binary.shape == continuous.shape == weight.shape):
        raise ValueError("utility and weight arrays must have the same shape")
    if np.unique(binary).size != 2 or not np.all(np.isfinite(continuous)) or not np.all(np.isfinite(weight)):
        raise ValueError("two-class binary utility and finite continuous arrays are required")
    auc = float(roc_auc_score(binary, weight))
    rho, p_value = spearmanr(continuous, weight)
    rng = np.random.default_rng(seed)
    auc_samples: list[float] = []
    rho_samples: list[float] = []
    for _ in range(n_resamples):
        indices = rng.integers(0, binary.size, size=binary.size)
        if np.unique(binary[indices]).size == 2:
            auc_samples.append(float(roc_auc_score(binary[indices], weight[indices])))
        sampled_rho = spearmanr(continuous[indices], weight[indices]).statistic
        if np.isfinite(sampled_rho):
            rho_samples.append(float(sampled_rho))
    if not auc_samples or not rho_samples:
        raise ValueError("no valid bootstrap samples")
    return {
        "utility_auc": auc,
        "utility_auc_ci_low": float(np.quantile(auc_samples, 0.025)),
        "utility_auc_ci_high": float(np.quantile(auc_samples, 0.975)),
        "spearman_rho": float(rho),
        "spearman_ci_low": float(np.quantile(rho_samples, 0.025)),
        "spearman_ci_high": float(np.quantile(rho_samples, 0.975)),
        "spearman_p": float(p_value),
    }
