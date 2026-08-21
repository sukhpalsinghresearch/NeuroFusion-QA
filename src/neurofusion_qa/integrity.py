"""Computational-integrity checks kept separate from scientific QC."""

from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np
from numpy.typing import ArrayLike


@dataclass(frozen=True)
class IntegrityReport:
    passed: bool
    expected_shape: tuple[int, ...]
    observed_shape: tuple[int, ...]
    all_finite: bool
    positive_variance: bool

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def validate_compact_features(
    features: ArrayLike, expected_shape: tuple[int, ...]
) -> IntegrityReport:
    """Check shape, finiteness, and non-degenerate variance without asserting QC."""
    array = np.asarray(features, dtype=float)
    shape_ok = array.shape == expected_shape
    finite = bool(np.all(np.isfinite(array)))
    variance = bool(finite and array.size > 1 and np.var(array) > 0.0)
    return IntegrityReport(
        passed=shape_ok and finite and variance,
        expected_shape=expected_shape,
        observed_shape=array.shape,
        all_finite=finite,
        positive_variance=variance,
    )

