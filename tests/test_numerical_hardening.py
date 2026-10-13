"""Regression tests for the four gaps exposed by the S01 release audit."""
import numpy as np
import pytest

from neurofusion_qa.features import fisher_connectivity, fmri_features_1440
from neurofusion_qa.gating import (
    binary_utility, continuous_utility, equal_fusion, label_free_quality_weight, soft_fusion,
)
from neurofusion_qa.quality import RobustQualityScaler


@pytest.mark.parametrize('operation', [
    lambda: equal_fusion([], []), lambda: soft_fusion([], [], []),
    lambda: continuous_utility([], [], []), lambda: binary_utility([], [], []),
    lambda: label_free_quality_weight([], []),
])
def test_empty_evidence_is_explicitly_rejected(operation):
    with pytest.raises(ValueError, match='nonempty'):
        operation()


@pytest.mark.parametrize('eeg,fmri,expected', [
    ([1e308], [1e308], [.5]),
    ([1e308, 0, 1], [0, 1e308, 3], [0, 1, .75]),
    ([np.finfo(float).max], [np.finfo(float).max / 2], [1 / 3]),
    (np.full((2, 3), 1e308), np.full((2, 3), 1e308), np.full((2, 3), .5)),
    (1e308, 1e308, .5),
])
def test_quality_normalization_does_not_overflow(eeg, fmri, expected):
    with np.errstate(over='raise', invalid='raise', divide='raise'):
        actual = label_free_quality_weight(eeg, fmri)
    np.testing.assert_allclose(actual, expected, rtol=1e-15, atol=0)
    assert np.isfinite(actual).all() and np.all((actual >= 0) & (actual <= 1))


def test_normal_quality_ratio_retains_original_arithmetic():
    rng = np.random.default_rng(20261011)
    eeg, fmri = rng.uniform(.01, 1, size=(2, 100))
    np.testing.assert_array_equal(label_free_quality_weight(eeg, fmri), fmri / (eeg + fmri))
    with pytest.raises(ValueError, match='positive quality'):
        label_free_quality_weight([1e-13], [1e-13])


@pytest.mark.parametrize('epsilon', [-1, np.nan, np.inf, -np.inf])
def test_invalid_normalization_epsilon_is_rejected(epsilon):
    with pytest.raises(ValueError, match='epsilon'):
        label_free_quality_weight([0], [0], epsilon=epsilon)


@pytest.mark.parametrize('infinite', [np.inf, -np.inf])
def test_infinite_training_quality_is_not_missingness(infinite):
    with pytest.raises(ValueError, match='infinite'):
        RobustQualityScaler.fit([[1], [infinite], [2]])


def test_training_nan_imputation_policy_is_preserved():
    scaler = RobustQualityScaler.fit([[1], [np.nan], [3]])
    np.testing.assert_array_equal(scaler.median, [2])
    np.testing.assert_array_equal(scaler.transform([[np.nan]]), [[0]])


@pytest.mark.parametrize('series,diagnostic', [
    (np.ones((3, 20)), 'constant'),
    ([[0, 1, 2], [3, 3, 3]], 'constant'),
    ([[0, 1, 2], [1, np.nan, 3]], 'non-finite'),
    ([[0, 1, 2], [1, np.inf, 3]], 'non-finite'),
    (np.empty((3, 0)), 'regions by samples'),
    (np.ones((3, 1)), 'regions by samples'),
])
def test_undefined_regional_correlations_fail_closed(series, diagnostic):
    with pytest.raises(ValueError, match=diagnostic):
        fisher_connectivity(series)


def test_valid_connectivity_retains_original_definition():
    series = np.random.default_rng(7).normal(size=(4, 30))
    expected = np.arctanh(np.clip(np.corrcoef(series), -.999999, .999999))
    np.fill_diagonal(expected, 0)
    np.testing.assert_array_equal(fisher_connectivity(series), expected)
    series[0] = 1
    with pytest.raises(ValueError, match='constant'):
        fmri_features_1440(np.tile(series, (90, 1)))
