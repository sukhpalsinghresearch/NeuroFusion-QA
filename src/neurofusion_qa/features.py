"""Data-free reference implementations of the frozen EEG and fMRI features."""

from __future__ import annotations

import numpy as np
from numpy.typing import ArrayLike, NDArray
from scipy.integrate import trapezoid
from scipy.signal import periodogram, welch


EEG_BANDS = ((1.0, 4.0), (4.0, 8.0), (8.0, 13.0), (13.0, 30.0), (30.0, 45.0))


def _entropy(probabilities: NDArray[np.float64], axis: int = -1) -> NDArray[np.float64]:
    p = np.clip(probabilities, 1e-15, None)
    p = p / np.sum(p, axis=axis, keepdims=True)
    return -np.sum(p * np.log(p), axis=axis) / np.log(p.shape[axis])


def eeg_features_33(signal: ArrayLike, sampling_rate: float = 250.0) -> NDArray[np.float64]:
    """Compute the order-independent 33-element EEG representation.

    Input is channels by samples and is assumed to have already passed the
    preprocessing/QC steps documented in the manuscript.
    """
    x = np.asarray(signal, dtype=float)
    if x.ndim != 2 or x.shape[0] < 2 or x.shape[1] < 2 * sampling_rate:
        raise ValueError("signal must be channels by samples with at least two seconds of data")
    if not np.all(np.isfinite(x)):
        raise ValueError("signal contains non-finite values")
    frequencies, psd = welch(
        x, fs=sampling_rate, window="hann", nperseg=int(2 * sampling_rate),
        noverlap=int(sampling_rate), detrend="constant", average="median", axis=-1,
    )
    bandpower = []
    for low, high in EEG_BANDS:
        mask = (frequencies >= low) & (frequencies <= high)
        bandpower.append(trapezoid(psd[:, mask], frequencies[mask], axis=1))
    powers = np.stack(bandpower, axis=1)
    spectral = np.asarray(
        [stat(powers[:, band]) for band in range(5) for stat in
         (np.median, lambda v: np.percentile(v, 75) - np.percentile(v, 25), np.std)],
        dtype=float,
    )
    medians = np.median(powers, axis=0)
    ratios = medians[[1, 3, 0]] / np.maximum(medians[2], 1e-15)
    analysis = (frequencies >= 1.0) & (frequencies <= 45.0)
    median_psd = np.median(psd[:, analysis], axis=0)
    analysis_f = frequencies[analysis]
    spectral_entropy = float(_entropy(median_psd))
    alpha = (analysis_f >= 8.0) & (analysis_f <= 14.0)
    alpha_peak = float(analysis_f[alpha][np.argmax(median_psd[alpha])])
    cumulative = np.cumsum(median_psd)
    edge95 = float(analysis_f[np.searchsorted(cumulative, 0.95 * cumulative[-1])])
    slope = float(np.polyfit(np.log10(analysis_f), np.log10(np.maximum(median_psd, 1e-15)), 1)[0])

    corr = np.corrcoef(x)
    upper = corr[np.triu_indices(corr.shape[0], k=1)]
    eigenvalues = np.clip(np.linalg.eigvalsh(corr), 0.0, None)
    corr_features = np.asarray([
        np.mean(upper), np.mean(np.abs(upper)), np.std(upper),
        np.percentile(upper, 10), np.percentile(upper, 50), np.percentile(upper, 90),
        np.max(eigenvalues) / np.maximum(np.sum(eigenvalues), 1e-15), _entropy(eigenvalues),
    ])
    dx = np.diff(x, axis=1)
    ddx = np.diff(dx, axis=1)
    activity = np.var(x, axis=1)
    mobility = np.sqrt(np.var(dx, axis=1) / np.maximum(activity, 1e-15))
    complexity = np.sqrt(np.var(ddx, axis=1) / np.maximum(np.var(dx, axis=1), 1e-15)) / np.maximum(mobility, 1e-15)
    hjorth = np.asarray([np.median(activity), np.median(mobility), np.median(complexity)])
    result = np.concatenate([spectral, ratios, [spectral_entropy, alpha_peak, edge95, slope], corr_features, hjorth])
    if result.shape != (33,) or not np.all(np.isfinite(result)):
        raise RuntimeError("EEG feature construction did not produce 33 finite values")
    return result


def fisher_connectivity(regional_series: ArrayLike) -> NDArray[np.float64]:
    """Return clipped Fisher-z correlations with a zero diagonal.

    Require at least two regions, two samples, and finite nonconstant rows.
    Constant rows have undefined Pearson correlations and are rejected rather
    than assigning a scientifically unsupported connectivity value.
    """
    series = np.asarray(regional_series, dtype=float)
    if series.ndim != 2 or series.shape[0] < 2 or series.shape[1] < 2:
        raise ValueError("regional_series must be regions by samples")
    if not np.all(np.isfinite(series)):
        raise ValueError("regional_series contains non-finite values")
    if np.any(np.all(series == series[:, :1], axis=1)):
        raise ValueError("regional_series contains constant rows with undefined correlations")
    corr = np.corrcoef(series)
    if not np.all(np.isfinite(corr)):
        raise ValueError("regional correlations must be finite")
    z = np.arctanh(np.clip(corr, -0.999999, 0.999999))
    np.fill_diagonal(z, 0.0)
    return z


def fmri_features_1440(regional_series: ArrayLike, sampling_rate: float = 1.25) -> NDArray[np.float64]:
    """Compute strength, ALFF, fALFF, and SD for 360 filtered regional series."""
    series = np.asarray(regional_series, dtype=float)
    if series.ndim != 2 or series.shape[0] != 360 or not np.all(np.isfinite(series)):
        raise ValueError("regional_series must contain 360 finite region-by-sample rows")
    connectivity = fisher_connectivity(series)
    strength = np.mean(connectivity, axis=1)
    frequencies, psd = periodogram(series, fs=sampling_rate, axis=-1, detrend="constant")
    amplitude = np.sqrt(np.maximum(psd, 0.0))
    low = (frequencies >= 0.01) & (frequencies <= 0.10)
    broad = (frequencies >= 0.01) & (frequencies <= 0.25)
    alff = np.sum(amplitude[:, low], axis=1)
    falff = alff / np.maximum(np.sum(amplitude[:, broad], axis=1), 1e-15)
    regional_sd = np.std(series, axis=1)
    result = np.concatenate([strength, alff, falff, regional_sd])
    if result.shape != (1440,) or not np.all(np.isfinite(result)):
        raise RuntimeError("fMRI feature construction did not produce 1440 finite values")
    return result
