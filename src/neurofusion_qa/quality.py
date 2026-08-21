"""Fold-specific quality transformations for label-free reliability gating."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import ArrayLike, NDArray
from scipy.special import expit


@dataclass(frozen=True)
class RobustQualityScaler:
    """Training-fold P10/P50/P90 scaler used in Eq. 10 of the manuscript."""

    median: NDArray[np.float64]
    p10: NDArray[np.float64]
    p90: NDArray[np.float64]
    clip: float = 5.0
    epsilon: float = 1e-12

    @classmethod
    def fit(cls, training_quality: ArrayLike, *, clip: float = 5.0) -> "RobustQualityScaler":
        values = np.asarray(training_quality, dtype=float)
        if values.ndim != 2 or values.shape[0] < 2:
            raise ValueError("training_quality must be a two-dimensional subject-by-variable array")
        if np.any(np.all(~np.isfinite(values), axis=0)):
            raise ValueError("each quality variable needs at least one finite training value")
        return cls(
            median=np.nanpercentile(values, 50, axis=0),
            p10=np.nanpercentile(values, 10, axis=0),
            p90=np.nanpercentile(values, 90, axis=0),
            clip=float(clip),
        )

    def transform(self, quality: ArrayLike) -> NDArray[np.float64]:
        """Median-impute, robustly scale, and clip without refitting."""
        values = np.asarray(quality, dtype=float)
        if values.ndim != 2 or values.shape[1] != self.median.size:
            raise ValueError("quality has an incompatible number of variables")
        imputed = np.where(np.isfinite(values), values, self.median)
        denominator = self.p90 - self.p10 + self.epsilon
        return np.clip((imputed - self.median) / denominator, -self.clip, self.clip)


def reliability_score(
    scaled_quality: ArrayLike,
    directions: ArrayLike,
    availability: ArrayLike | None = None,
) -> NDArray[np.float64]:
    """Return availability times sigmoid(mean directed quality), Eq. 11."""
    quality = np.asarray(scaled_quality, dtype=float)
    direction = np.asarray(directions, dtype=float)
    if quality.ndim != 2 or direction.shape != (quality.shape[1],):
        raise ValueError("directions must contain one value per quality variable")
    if not np.all(np.isin(direction, (-1.0, 1.0))):
        raise ValueError("directions must contain only -1 or +1")
    if not np.all(np.isfinite(quality)):
        raise ValueError("scaled_quality contains non-finite values")
    available = np.ones(quality.shape[0], dtype=float)
    if availability is not None:
        available = np.asarray(availability, dtype=float)
        if available.shape != (quality.shape[0],) or not np.all(np.isin(available, (0.0, 1.0))):
            raise ValueError("availability must be a binary subject-level vector")
    return available * expit(np.mean(quality * direction, axis=1))

