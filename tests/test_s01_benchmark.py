import importlib.util
from pathlib import Path

import numpy as np
import pytest
from sklearn import metrics

PATH = Path(__file__).resolve().parents[1] / "scripts/s01_comparator_benchmark.py"
SPEC = importlib.util.spec_from_file_location("s01_benchmark", PATH)
benchmark = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(benchmark)


def test_frozen_protocol():
    assert benchmark.load_protocol()["protocol_id"]


@pytest.mark.parametrize("probability", [[0, .8, .2, 1, .7, .1], [.3, .2, .7, .6, .2, .9]])
def test_metrics_agree_with_reference(probability):
    y = np.array([0, 1, 0, 1, 0, 1])
    p = np.array(probability)
    d = (p >= .5).astype(int)
    actual = benchmark.metric_arrays(y, p, d)
    expected = {
        "roc_auc": metrics.roc_auc_score(y, p),
        "average_precision": metrics.average_precision_score(y, p),
        "brier_score": metrics.brier_score_loss(y, p),
        "log_loss": metrics.log_loss(y, np.clip(p, 1e-6, 1 - 1e-6)),
        "accuracy": metrics.accuracy_score(y, d),
        "balanced_accuracy": metrics.balanced_accuracy_score(y, d),
        "precision": metrics.precision_score(y, d, zero_division=0),
        "sensitivity": metrics.recall_score(y, d, zero_division=0),
        "specificity": metrics.recall_score(y, d, pos_label=0, zero_division=0),
        "f1": metrics.f1_score(y, d, zero_division=0),
        "mcc": metrics.matthews_corrcoef(y, d),
    }
    for name, value in expected.items():
        np.testing.assert_allclose(actual[name], [value], atol=1e-12)
    bins = np.minimum((p * 10).astype(int), 9)
    ece = sum(abs(np.sum((p - y)[bins == b])) / len(y) for b in range(10))
    np.testing.assert_allclose(actual["ece_10_uniform"], [ece])


def test_features_do_not_change_with_quality_condition():
    protocol = benchmark.load_protocol()
    first = benchmark.fixture(protocol, 1201, "informative")
    for condition in ("unrelated", "misleading"):
        other = benchmark.fixture(protocol, 1201, condition)
        np.testing.assert_array_equal(first[0], other[0])
        for name in ("eeg", "fmri"):
            np.testing.assert_array_equal(first[1][name], other[1][name])
    np.testing.assert_allclose(first[2] + benchmark.fixture(protocol, 1201, "misleading")[2], 1)


def test_bootstrap_preserves_seed_class_counts_and_is_replayable():
    y = np.tile([0, 1], 12)
    strata = np.repeat([10, 11, 12], 8)
    ids = benchmark.stratified_indices(y, strata, 30, 22)
    np.testing.assert_array_equal(ids, benchmark.stratified_indices(y, strata, 30, 22))
    for s in np.unique(strata):
        for label in (0, 1):
            assert np.all(np.sum((strata[ids] == s) & (y[ids] == label), axis=1) == 4)


def test_shared_splits_and_unimodal_predictions_across_conditions():
    protocol = benchmark.load_protocol()
    protocol["records_per_fixture"] = 40
    protocol["c_grid"] = [.1]
    protocol["splits"].update(outer_repeats=1, outer_folds=2, inner_folds=2)
    a = benchmark.nested_predictions(protocol, 1201, "informative")
    b = benchmark.nested_predictions(protocol, 1201, "misleading")
    for name in ("eeg", "fmri", "equal", "tuned_constant"):
        np.testing.assert_array_equal(a[1][name], b[1][name])
    assert [(f["train_hash"], f["test_hash"]) for f in a[4]] == [(f["train_hash"], f["test_hash"]) for f in b[4]]
    for probability in a[1].values():
        assert probability.shape == (40,) and np.isfinite(probability).all()


def test_no_positive_decisions_metric_convention():
    result = benchmark.metric_arrays(np.array([0, 1, 0, 1]), np.full(4, .2), np.zeros(4))
    for name in ("precision", "f1", "mcc"):
        assert result[name][0] == 0
