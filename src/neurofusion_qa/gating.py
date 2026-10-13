"""Fusion and utility equations used by NeuroFusion-QA."""

from __future__ import annotations

import numpy as np
from numpy.typing import ArrayLike, NDArray


def _as_probability(values: ArrayLike, name: str) -> NDArray[np.float64]:
    array = np.asarray(values, dtype=float)
    if array.size == 0:
        raise ValueError(f"{name} must be nonempty")
    if not np.all(np.isfinite(array)):
        raise ValueError(f"{name} contains non-finite values")
    if np.any((array < 0.0) | (array > 1.0)):
        raise ValueError(f"{name} must lie in [0, 1]")
    return array


def equal_fusion(p_eeg: ArrayLike, p_fmri: ArrayLike) -> NDArray[np.float64]:
    """Average two matched, nonempty unimodal probability arrays."""
    eeg = _as_probability(p_eeg, "p_eeg")
    fmri = _as_probability(p_fmri, "p_fmri")
    if eeg.shape != fmri.shape:
        raise ValueError("unimodal probabilities must have the same shape")
    return 0.5 * (eeg + fmri)


def soft_fusion(
    p_eeg: ArrayLike, p_fmri: ArrayLike, w_fmri: ArrayLike
) -> NDArray[np.float64]:
    """Fuse matched probabilities using a subject-level fMRI contribution."""
    eeg = _as_probability(p_eeg, "p_eeg")
    fmri = _as_probability(p_fmri, "p_fmri")
    weight = _as_probability(w_fmri, "w_fmri")
    if not (eeg.shape == fmri.shape == weight.shape):
        raise ValueError("probabilities and weights must have the same shape")
    return (1.0 - weight) * eeg + weight * fmri


def label_free_quality_weight(
    eeg_quality: ArrayLike, fmri_quality: ArrayLike, epsilon: float = 1e-12
) -> NDArray[np.float64]:
    """Normalize nonempty, finite nonnegative quality masses into fMRI weights.

    Total quality must exceed finite nonnegative ``epsilon``. Large masses are
    halved together before summation to avoid overflow without changing ratios.
    """
    eeg = np.asarray(eeg_quality, dtype=float)
    fmri = np.asarray(fmri_quality, dtype=float)
    if eeg.shape != fmri.shape:
        raise ValueError("quality arrays must have the same shape")
    if eeg.size == 0:
        raise ValueError("quality arrays must be nonempty")
    if not np.isfinite(epsilon) or epsilon < 0:
        raise ValueError("epsilon must be finite and non-negative")
    if not np.all(np.isfinite(eeg)) or not np.all(np.isfinite(fmri)):
        raise ValueError("quality arrays contain non-finite values")
    if np.any(eeg < 0.0) or np.any(fmri < 0.0):
        raise ValueError("quality scores must be non-negative")
    large = np.maximum(eeg, fmri) > np.finfo(float).max / 2
    safe_eeg = np.where(large, eeg * 0.5, eeg)
    safe_fmri = np.where(large, fmri * 0.5, fmri)
    denominator = safe_eeg + safe_fmri
    if np.any(denominator <= np.where(large, epsilon * 0.5, epsilon)):
        raise ValueError("at least one modality must have positive quality")
    return safe_fmri / denominator


def continuous_utility(
    y_true: ArrayLike, p_eeg: ArrayLike, p_fmri: ArrayLike
) -> NDArray[np.float64]:
    """Return held-out fMRI benefit: |y-p_EEG| - |y-p_fMRI|."""
    y = _as_probability(y_true, "y_true")
    eeg = _as_probability(p_eeg, "p_eeg")
    fmri = _as_probability(p_fmri, "p_fmri")
    if not (y.shape == eeg.shape == fmri.shape):
        raise ValueError("labels and probabilities must have the same shape")
    return np.abs(y - eeg) - np.abs(y - fmri)


def binary_utility(
    y_true: ArrayLike, p_eeg: ArrayLike, p_fmri: ArrayLike
) -> NDArray[np.int_]:
    """Return one when held-out fMRI absolute error is lower than EEG error."""
    return (continuous_utility(y_true, p_eeg, p_fmri) > 0.0).astype(int)

