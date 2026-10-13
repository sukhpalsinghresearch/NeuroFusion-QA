"""Executable synthetic contracts shared by notebook 01 and integration tests.

Fixtures are mathematical software tests. No study data or aggregate results
are loaded. Functions return JSON-compatible evidence without row-level outputs.
"""

from __future__ import annotations

from dataclasses import asdict, replace
import hashlib

import numpy as np
from sklearn.metrics import brier_score_loss
from sklearn.model_selection import StratifiedKFold

from neurofusion_qa.gating import (
    binary_utility, continuous_utility, equal_fusion,
    label_free_quality_weight, soft_fusion,
)
from neurofusion_qa.integrity import validate_compact_features
from neurofusion_qa.modeling import (
    C_GRID, average_repeated_predictions, make_classifier,
    select_balanced_threshold,
)
from neurofusion_qa.provenance import canonical_json_sha256
from neurofusion_qa.qc import FmriQcMeasurements, evaluate_fmri_qc
from neurofusion_qa.quality import RobustQualityScaler, reliability_score


def qc_contracts() -> dict:
    """Check each declared criterion at the boundary and on either side."""
    baseline = FmriQcMeasurements(0.10, 0.90, 2.0, 360, 360, True, 0.1)
    cases = {
        "censored_fraction": [(0.19, True), (0.20, True), (0.21, False)],
        "registration_dice": [(0.69, False), (0.70, True), (0.71, True)],
        "centroid_distance_mm": [(7.9, True), (8.0, True), (8.1, False)],
        "parcels_present": [(356, False), (357, True), (358, True)],
        "parcels_with_10_voxels": [(357, False), (358, True), (359, True)],
        "finite_connectome": [(False, False), (True, True)],
        "minimum_filtered_regional_sd": [(-0.01, False), (0.0, False), (0.01, True)],
    }
    rows = []
    for criterion, values in cases.items():
        for value, expected in values:
            report = evaluate_fmri_qc(replace(baseline, **{criterion: value}))
            assert report.passed == expected, (criterion, value)
            assert report.criteria[criterion] == expected
            assert all(passed for key, passed in report.criteria.items() if key != criterion)
            rows.append({"criterion": criterion, "value": value,
                         "expected_pass": expected, "observed_pass": report.passed})
    integrity_pass = validate_compact_features([1, 2, 3], (3,))
    integrity_fail = validate_compact_features([1, 1, 1], (3,))
    qc_pass = evaluate_fmri_qc(baseline)
    qc_fail = evaluate_fmri_qc(replace(baseline, censored_fraction=0.21))
    independent_gates = [
        {"integrity_pass": integrity.passed, "scientific_qc_pass": qc.passed}
        for integrity in (integrity_pass, integrity_fail)
        for qc in (qc_pass, qc_fail)
    ]
    assert len({(row["integrity_pass"], row["scientific_qc_pass"])
                for row in independent_gates}) == 4
    return {"baseline_measurements": asdict(baseline),
            "threshold_cases": rows, "independent_gates": independent_gates}


def quality_contracts() -> dict:
    """Demonstrate training-only fitting, imputation, clipping and availability."""
    training = np.array([[0, 10], [1, 20], [2, np.nan], [3, 40]], dtype=float)
    scaler = RobustQualityScaler.fit(training)
    frozen = [values.copy() for values in (scaler.median, scaler.p10, scaler.p90)]
    held_out = np.array([[1.5, np.nan], [1e6, -1e6]], dtype=float)
    scaled = scaler.transform(held_out)
    np.testing.assert_allclose(scaled[0], [0, 0])
    np.testing.assert_allclose(scaled[1], [5, -5])
    scaler.transform(held_out * 100)
    for original, current in zip(frozen, (scaler.median, scaler.p10, scaler.p90)):
        np.testing.assert_array_equal(original, current)
    leaky = RobustQualityScaler.fit(np.vstack([training, held_out]))
    assert not np.array_equal(leaky.p90, scaler.p90)
    scores = reliability_score(scaled, [1, -1], availability=[1, 0])
    np.testing.assert_allclose(scores, [0.5, 0])
    # The same directed quality moved upward must increase its score.
    increasing = reliability_score([[0, 0], [1, -1]], [1, -1])
    assert increasing[1] > increasing[0]
    return {"training_median": scaler.median.tolist(),
            "training_p10": scaler.p10.tolist(), "training_p90": scaler.p90.tolist(),
            "scaled_held_out": scaled.tolist(), "availability_scores": scores.tolist(),
            "held_out_transform_preserves_fit": True,
            "leaky_refit_changes_percentiles": True,
            "quality_path_uses_labels": False}


def fusion_contracts(seed: int = 20260918) -> dict:
    """Check fusion invariants and require specific diagnostics for failures."""
    rng = np.random.default_rng(seed)
    eeg, fmri = rng.uniform(size=(2, 512))
    q_eeg, q_fmri = rng.uniform(0.01, 1, size=(2, 512))
    weight = label_free_quality_weight(q_eeg, q_fmri)
    fused = soft_fusion(eeg, fmri, weight)
    np.testing.assert_allclose(weight + (1 - weight), 1)
    assert np.all((fused >= 0) & (fused <= 1))
    np.testing.assert_allclose(soft_fusion(eeg, fmri, np.zeros(512)), eeg)
    np.testing.assert_allclose(soft_fusion(eeg, fmri, np.ones(512)), fmri)
    np.testing.assert_allclose(soft_fusion(eeg, fmri, np.full(512, 0.5)), equal_fusion(eeg, fmri))
    np.testing.assert_allclose(label_free_quality_weight([1, 0], [0, 1]), [0, 1])
    labels = rng.integers(0, 2, size=512)
    utility = continuous_utility(labels, eeg, fmri)
    np.testing.assert_array_equal(binary_utility(labels, eeg, fmri), utility > 0)
    _ = soft_fusion(eeg, fmri, 1 - weight)
    np.testing.assert_array_equal(continuous_utility(labels, eeg, fmri), utility)
    invalid_cases = [
        ("nonfinite_probability", lambda: equal_fusion([np.nan], [0.4]), "non-finite"),
        ("infinite_probability", lambda: equal_fusion([np.inf], [0.4]), "non-finite"),
        ("probability_outside_bounds", lambda: equal_fusion([1.1], [0.4]), "[0, 1]"),
        ("probability_shape", lambda: equal_fusion([0.2, 0.3], [0.4]), "same shape"),
        ("invalid_weight", lambda: soft_fusion([0.2], [0.4], [-0.1]), "[0, 1]"),
        ("negative_quality", lambda: label_free_quality_weight([-1], [1]), "non-negative"),
        ("zero_total_quality", lambda: label_free_quality_weight([0], [0]), "positive quality"),
        ("invalid_direction", lambda: reliability_score([[0, 1]], [0, 1]), "-1 or +1"),
        ("invalid_availability", lambda: reliability_score([[0, 1]], [1, -1], [0.5]), "binary"),
    ]
    failures = []
    for name, operation, diagnostic in invalid_cases:
        try:
            operation()
        except ValueError as error:
            assert diagnostic in str(error), (name, str(error))
            failures.append({"case": name, "exception": "ValueError", "message": str(error)})
        else:
            raise AssertionError(f"Invalid case was accepted: {name}")
    return {"generated_valid_cases": 512, "weight_normalization": True,
            "probability_bounds": True, "endpoint_recovery": True,
            "utility_independent_of_gate": True, "failures": failures}


def synthetic_model_fixture(seed: int = 20260918, n_records: int = 80) -> dict:
    """Generate compact paired arrays, independently of the signal examples.

    These arrays exercise model interfaces; they are not EEG/fMRI feature
    extraction outputs, observations of people, or a benchmark dataset.
    """
    rng = np.random.default_rng(seed)
    labels = np.arange(n_records) % 2
    rng.shuffle(labels)
    contrast = (2 * labels - 1)[:, None]
    eeg = rng.normal(size=(n_records, 6)) + contrast * np.array([0.8, 0.4, 0, 0, 0, 0])
    fmri = rng.normal(size=(n_records, 8)) + contrast * np.array([0.6, 0.5, 0.2, 0, 0, 0, 0, 0])
    eeg[::17, 2] = np.nan
    fmri[::13, 3] = np.nan
    quality = rng.uniform(size=(n_records, 4))
    quality[::9, 1] = np.nan
    return {"labels": labels, "eeg": eeg, "fmri": fmri, "quality": quality}


def matched_model_contracts(seed: int = 1201, repeats: int = 2) -> dict:
    """Exercise matched nested splits with training-only tuning and scaling."""
    fixture = synthetic_model_fixture()
    labels = fixture["labels"]
    n_records = labels.size
    predictions = {name: np.full((repeats, n_records), np.nan)
                   for name in ("eeg", "fmri", "equal", "quality")}
    seen = np.zeros((repeats, n_records), dtype=int)
    fold_reports = []
    for repeat in range(repeats):
        outer = StratifiedKFold(4, shuffle=True, random_state=seed + repeat)
        for fold, (train, test) in enumerate(outer.split(fixture["eeg"], labels)):
            assert not np.intersect1d(train, test).size
            assert np.unique(labels[train]).size == np.unique(labels[test]).size == 2
            seen[repeat, test] += 1
            inner = list(StratifiedKFold(3, shuffle=True, random_state=seed + repeat)
                         .split(fixture["eeg"][train], labels[train]))
            tuning = {}
            for modality in ("eeg", "fmri"):
                values = fixture[modality]
                inner_predictions = []
                losses = []
                for c in C_GRID:
                    oof = np.full(train.size, np.nan)
                    for fit_local, valid_local in inner:
                        fit_ids, valid_ids = train[fit_local], train[valid_local]
                        assert not np.intersect1d(fit_ids, test).size
                        assert not np.intersect1d(valid_ids, test).size
                        model = make_classifier(c=c, seed=seed)
                        model.fit(values[fit_ids], labels[fit_ids])
                        oof[valid_local] = model.predict_proba(values[valid_ids])[:, 1]
                    assert np.all(np.isfinite(oof))
                    losses.append(brier_score_loss(labels[train], oof))
                    inner_predictions.append(oof)
                best = int(np.argmin(losses))
                threshold = select_balanced_threshold(labels[train], inner_predictions[best])
                model = make_classifier(c=C_GRID[best], seed=seed)
                model.fit(values[train], labels[train])
                predictions[modality][repeat, test] = model.predict_proba(values[test])[:, 1]
                np.testing.assert_allclose(model.named_steps["imputer"].statistics_,
                                           np.nanmedian(values[train], axis=0))
                tuning[modality] = {"selected_c": C_GRID[best],
                                    "training_oof_threshold": threshold,
                                    "threshold_input_records": int(train.size)}
            quality = fixture["quality"]
            scaler = RobustQualityScaler.fit(quality[train])
            np.testing.assert_allclose(scaler.median, np.nanmedian(quality[train], axis=0))
            scaled = scaler.transform(quality[test])
            q_eeg = reliability_score(scaled[:, :2], [1, -1])
            q_fmri = reliability_score(scaled[:, 2:], [1, -1])
            weight = label_free_quality_weight(q_eeg, q_fmri)
            eeg = predictions["eeg"][repeat, test]
            fmri = predictions["fmri"][repeat, test]
            predictions["equal"][repeat, test] = equal_fusion(eeg, fmri)
            predictions["quality"][repeat, test] = soft_fusion(eeg, fmri, weight)
            fold_reports.append({
                "repeat": repeat, "fold": fold, "training_records": int(train.size),
                "held_out_records": int(test.size), "inner_folds": len(inner),
                "training_index_sha256": canonical_json_sha256(train.tolist()),
                "held_out_index_sha256": canonical_json_sha256(test.tolist()),
                "train_test_disjoint": True, "shared_modality_splits": True,
                "quality_fit_on_training_only": True, "tuning": tuning,
            })
    np.testing.assert_array_equal(seen, np.ones_like(seen))
    summaries = {}
    for name, values in predictions.items():
        assert np.all(np.isfinite(values)) and np.all((values >= 0) & (values <= 1))
        average = average_repeated_predictions(values)
        np.testing.assert_allclose(average, values.mean(axis=0))
        # Hash a rounded representation: bitwise cross-platform identity is not claimed.
        summaries[name] = {"repeat_shape": list(values.shape),
                           "averaged_shape": list(average.shape),
                           "minimum": float(average.min()), "maximum": float(average.max()),
                           "rounded_probability_sha256": hashlib.sha256(
                               np.round(values, 12).astype('<f8').tobytes()).hexdigest()}
    return {"fixture_kind": "independent_synthetic_compact_interface_arrays",
            "fixture_seed": 20260918, "model_seed": seed,
            "records": int(n_records), "outer_folds": 4, "outer_repeats": repeats,
            "inner_folds": 3, "selection_metric": "training_oof_brier_score",
            "threshold_source": "selected_model_training_oof_predictions",
            "each_record_held_out_once_per_repeat": True,
            "benchmark_metrics_reported": False,
            "folds": fold_reports, "predictions": summaries}
