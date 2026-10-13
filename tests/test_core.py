import numpy as np
import pytest

from neurofusion_qa.gating import (
    binary_utility,
    continuous_utility,
    equal_fusion,
    label_free_quality_weight,
    soft_fusion,
)
from neurofusion_qa.integrity import validate_compact_features
from neurofusion_qa.features import eeg_features_33, fisher_connectivity, fmri_features_1440
from neurofusion_qa.modeling import average_repeated_predictions, make_classifier, select_balanced_threshold
from neurofusion_qa.qc import FmriQcMeasurements, evaluate_fmri_qc
from neurofusion_qa.quality import RobustQualityScaler, reliability_score


def test_equal_and_soft_fusion() -> None:
    eeg = np.array([0.2, 0.8])
    fmri = np.array([0.6, 0.4])
    np.testing.assert_allclose(equal_fusion(eeg, fmri), [0.4, 0.6])
    np.testing.assert_allclose(soft_fusion(eeg, fmri, [0.25, 0.75]), [0.3, 0.5])


def test_quality_weight_normalization() -> None:
    np.testing.assert_allclose(label_free_quality_weight([3.0, 1.0], [1.0, 3.0]), [0.25, 0.75])


def test_utility_is_independent_of_gate() -> None:
    y = [0, 1]
    eeg = [0.1, 0.6]
    fmri = [0.3, 0.9]
    np.testing.assert_allclose(continuous_utility(y, eeg, fmri), [-0.2, 0.3])
    np.testing.assert_array_equal(binary_utility(y, eeg, fmri), [0, 1])


def test_integrity_does_not_assert_scientific_qc() -> None:
    report = validate_compact_features([1.0, 2.0, 3.0], expected_shape=(3,))
    assert report.passed
    assert "qc" not in report.to_dict()


def test_nonfinite_probability_is_rejected() -> None:
    with pytest.raises(ValueError):
        equal_fusion([0.2, np.nan], [0.3, 0.4])


def test_training_fold_quality_scaling_and_availability() -> None:
    train = np.array([[0.0, 10.0], [1.0, 20.0], [2.0, np.nan], [3.0, 40.0]])
    scaler = RobustQualityScaler.fit(train)
    scaled = scaler.transform([[1.5, np.nan], [3.0, 10.0]])
    score = reliability_score(scaled, [1, -1], availability=[1, 0])
    assert score.shape == (2,)
    assert 0.0 < score[0] < 1.0
    assert score[1] == 0.0


def test_qc_is_a_strict_conjunction() -> None:
    passing = FmriQcMeasurements(0.20, 0.70, 8.0, 357, 358, True, 0.01)
    assert evaluate_fmri_qc(passing).passed
    failing = FmriQcMeasurements(0.21, 0.70, 8.0, 357, 358, True, 0.01)
    assert not evaluate_fmri_qc(failing).passed


def test_frozen_model_helpers() -> None:
    assert make_classifier(c=1.0).named_steps["classifier"].class_weight == "balanced"
    assert 0.05 <= select_balanced_threshold([0, 0, 1, 1], [0.1, 0.4, 0.6, 0.9]) <= 0.95
    np.testing.assert_allclose(average_repeated_predictions([[0.2, 0.8], [0.4, 0.6]]), [0.3, 0.7])


def test_feature_dimensions() -> None:
    rng = np.random.default_rng(7)
    eeg = rng.normal(size=(8, 1000))
    assert eeg_features_33(eeg).shape == (33,)
    regional = rng.normal(size=(360, 120))
    assert fisher_connectivity(regional).shape == (360, 360)
    assert fmri_features_1440(regional).shape == (1440,)


def test_eeg_bandpower_is_numpy_2_compatible() -> None:
    """Regression test for the removal of numpy.trapz in NumPy 2.x."""
    time = np.arange(1000, dtype=float) / 250.0
    signal = np.vstack([
        np.sin(2.0 * np.pi * frequency * time)
        for frequency in (3.0, 6.0, 10.0, 18.0)
    ])
    features = eeg_features_33(signal)
    assert features.shape == (33,)
    assert np.all(np.isfinite(features))
