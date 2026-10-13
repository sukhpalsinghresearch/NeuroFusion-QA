"""Frozen controlled synthetic comparison; no population or external-tool claims."""

from __future__ import annotations

import argparse
import json
import platform
import time
from importlib.metadata import version
from pathlib import Path

import numpy as np
from scipy.stats import spearmanr
from sklearn.metrics import average_precision_score, brier_score_loss, precision_recall_curve, roc_auc_score, roc_curve
from sklearn.model_selection import StratifiedKFold
from threadpoolctl import threadpool_info, threadpool_limits

from neurofusion_qa.gating import continuous_utility, equal_fusion, label_free_quality_weight, soft_fusion
from neurofusion_qa.modeling import make_classifier, select_balanced_threshold
from neurofusion_qa.provenance import canonical_json, canonical_json_sha256, sha256_file
from neurofusion_qa.quality import RobustQualityScaler, reliability_score

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_HASH = "c492d518958916df3998c5dac11cb0e01c4734481de9669e429ed3d3ebb0849b"
PROTOCOL_COMMIT = "c4d0ca6"
METHODS = ("eeg", "fmri", "equal", "quality", "tuned_constant")


def load_protocol():
    protocol = json.loads((ROOT / "config/s01_comparator_protocol.json").read_text(encoding="utf-8"))
    if canonical_json_sha256(protocol) != PROTOCOL_HASH:
        raise ValueError("Frozen comparator protocol hash mismatch")
    return protocol


def fixture(protocol, seed, condition):
    rng = np.random.default_rng(seed)
    labels = np.arange(protocol["records_per_fixture"]) % 2
    rng.shuffle(labels)
    degradation = rng.uniform(size=(labels.size, 2))
    quality_unrelated = rng.uniform(size=(labels.size, 2))
    values = {}
    for index, modality in enumerate(("eeg", "fmri")):
        coefficients = np.array(protocol["signal_coefficients"][modality])
        sigma = 0.4 + 2.4 * degradation[:, index]
        values[modality] = rng.normal(size=(labels.size, coefficients.size)) * sigma[:, None]
        values[modality] += (2 * labels - 1)[:, None] * coefficients
    quality = {"informative": 1 - degradation, "unrelated": quality_unrelated,
               "misleading": degradation}[condition]
    return labels, values, quality


def quality_weights(quality, train, test):
    scaler = RobustQualityScaler.fit(quality[train])
    transformed = scaler.transform(quality[test])
    first = reliability_score(transformed[:, :1], [1])
    second = reliability_score(transformed[:, 1:], [1])
    return label_free_quality_weight(first, second)


def nested_predictions(protocol, seed, condition):
    labels, values, quality = fixture(protocol, seed, condition)
    repeats = protocol["splits"]["outer_repeats"]
    predictions = {name: np.full((repeats, labels.size), np.nan) for name in METHODS}
    decisions = {name: np.zeros((repeats, labels.size), dtype=int) for name in METHODS}
    weights = np.full((repeats, labels.size), np.nan)
    seen = np.zeros((repeats, labels.size), dtype=int)
    reports = []
    model_seed = protocol["splits"]["model_seed"]
    for repeat in range(repeats):
        outer = StratifiedKFold(protocol["splits"]["outer_folds"], shuffle=True, random_state=model_seed + repeat)
        for fold, (train, test) in enumerate(outer.split(values["eeg"], labels)):
            assert not np.intersect1d(train, test).size
            seen[repeat, test] += 1
            inner = list(StratifiedKFold(protocol["splits"]["inner_folds"], shuffle=True, random_state=model_seed + repeat)
                         .split(values["eeg"][train], labels[train]))
            oof = {}
            selected = {}
            for modality in ("eeg", "fmri"):
                candidates, losses = [], []
                for c in protocol["c_grid"]:
                    candidate = np.full(train.size, np.nan)
                    for fit, valid in inner:
                        model = make_classifier(c=c, seed=model_seed)
                        model.fit(values[modality][train[fit]], labels[train[fit]])
                        candidate[valid] = model.predict_proba(values[modality][train[valid]])[:, 1]
                    assert np.isfinite(candidate).all()
                    candidates.append(candidate)
                    losses.append(brier_score_loss(labels[train], candidate))
                best = int(np.argmin(losses))
                selected[modality] = protocol["c_grid"][best]
                oof[modality] = candidates[best]
                model = make_classifier(c=selected[modality], seed=model_seed)
                model.fit(values[modality][train], labels[train])
                predictions[modality][repeat, test] = model.predict_proba(values[modality][test])[:, 1]
            inner_weight = np.full(train.size, np.nan)
            for fit, valid in inner:
                inner_weight[valid] = quality_weights(quality, train[fit], train[valid])
            grid = protocol["constant_weight_grid"]
            losses = [brier_score_loss(labels[train], soft_fusion(oof["eeg"], oof["fmri"], np.full(train.size, w))) for w in grid]
            minimizers = np.flatnonzero(np.isclose(losses, min(losses), rtol=0, atol=1e-12))
            best = min(minimizers, key=lambda i: (abs(grid[i] - 0.5), grid[i]))
            constant = grid[best]
            weights[repeat, test] = quality_weights(quality, train, test)
            oof["equal"] = equal_fusion(oof["eeg"], oof["fmri"])
            oof["quality"] = soft_fusion(oof["eeg"], oof["fmri"], inner_weight)
            oof["tuned_constant"] = soft_fusion(oof["eeg"], oof["fmri"], np.full(train.size, constant))
            eeg, fmri = predictions["eeg"][repeat, test], predictions["fmri"][repeat, test]
            predictions["equal"][repeat, test] = equal_fusion(eeg, fmri)
            predictions["quality"][repeat, test] = soft_fusion(eeg, fmri, weights[repeat, test])
            predictions["tuned_constant"][repeat, test] = soft_fusion(eeg, fmri, np.full(test.size, constant))
            thresholds = {}
            for name in METHODS:
                threshold = select_balanced_threshold(labels[train], oof[name])
                thresholds[name] = threshold
                decisions[name][repeat, test] = predictions[name][repeat, test] >= threshold
            reports.append({"condition": condition, "fixture_seed": seed, "repeat": repeat, "fold": fold,
                            "train_count": int(train.size), "test_count": int(test.size),
                            "train_hash": canonical_json_sha256(train.tolist()), "test_hash": canonical_json_sha256(test.tolist()),
                            "selected_c": selected, "constant_weight": constant, "thresholds": thresholds})
    assert np.array_equal(seen, np.ones_like(seen))
    assert all(np.isfinite(p).all() and ((p >= 0) & (p <= 1)).all() for p in predictions.values())
    return labels, {name: p.mean(axis=0) for name, p in predictions.items()}, {
        name: (votes.mean(axis=0) >= 0.5).astype(int) for name, votes in decisions.items()
    }, weights.mean(axis=0), reports


def metric_arrays(y, p, decision):
    """Compute all metrics for one or many bootstrap rows; no row filtering."""
    y, p, decision = (np.atleast_2d(values) for values in (y, p, decision))
    tp = np.sum((y == 1) & (decision == 1), axis=1)
    tn = np.sum((y == 0) & (decision == 0), axis=1)
    fp = np.sum((y == 0) & (decision == 1), axis=1)
    fn = np.sum((y == 1) & (decision == 0), axis=1)
    divide = lambda a, b: np.divide(a, b, out=np.zeros(a.shape, dtype=float), where=b != 0)
    sensitivity, specificity = divide(tp, tp + fn), divide(tn, tn + fp)
    clipped = np.clip(p, 1e-6, 1 - 1e-6)
    ece = np.zeros(y.shape[0])
    bins = np.minimum((p * 10).astype(int), 9)
    for bin_id in range(10):
        member = bins == bin_id
        # count/n * abs(mean(p)-mean(y)) = abs(sum(p-y))/n.
        ece += np.abs(np.sum((p - y) * member, axis=1)) / y.shape[1]
    return {
        "roc_auc": np.array([roc_auc_score(a, b) for a, b in zip(y, p)]),
        "average_precision": np.array([average_precision_score(a, b) for a, b in zip(y, p)]),
        "brier_score": np.mean((p - y) ** 2, axis=1),
        "log_loss": -np.mean(y * np.log(clipped) + (1 - y) * np.log(1 - clipped), axis=1),
        "accuracy": (tp + tn) / y.shape[1], "balanced_accuracy": (sensitivity + specificity) / 2,
        "precision": divide(tp, tp + fp), "sensitivity": sensitivity, "specificity": specificity,
        "f1": divide(2 * tp, 2 * tp + fp + fn),
        "mcc": divide(tp * tn - fp * fn, np.sqrt((tp + fp) * (tp + fn) * (tn + fp) * (tn + fn))),
        "ece_10_uniform": ece,
    }


def stratified_indices(labels, strata, resamples, seed):
    rng = np.random.default_rng(seed)
    groups = [np.flatnonzero((strata == s) & (labels == c)) for s in np.unique(strata) for c in (0, 1)]
    assert all(len(group) for group in groups)
    return np.concatenate([rng.choice(group, size=(resamples, group.size), replace=True) for group in groups], axis=1)


def summaries(protocol, labels, probabilities, decisions, strata, weights):
    indices = stratified_indices(labels, strata, protocol["uncertainty"]["resamples"], protocol["uncertainty"]["seed"])
    rows, profiles, curves, confusion, calibration = [], {}, {}, {}, {}
    bootstrap = {}
    for name in METHODS:
        p, d = probabilities[name], decisions[name]
        point = metric_arrays(labels, p, d)
        bootstrap[name] = metric_arrays(labels[indices], p[indices], d[indices])
        profiles[name] = {}
        for metric, value in point.items():
            low, high = np.quantile(bootstrap[name][metric], [0.025, 0.975])
            profiles[name][metric] = {"value": float(value[0]), "ci_low": float(low), "ci_high": float(high)}
        fpr, tpr, _ = roc_curve(labels, p)
        precision, recall, _ = precision_recall_curve(labels, p)
        curves[name] = {"fpr": fpr.tolist(), "tpr": tpr.tolist(), "precision": precision.tolist(), "recall": recall.tolist()}
        confusion[name] = [[int(np.sum((labels == a) & (d == b))) for b in (0, 1)] for a in (0, 1)]
        bins = np.minimum((p * 10).astype(int), 9)
        calibration[name] = []
        for index in range(10):
            member = bins == index
            calibration[name].append({"bin": index, "count": int(member.sum()),
                "mean_probability": float(p[member].mean()) if member.any() else None,
                "positive_fraction": float(labels[member].mean()) if member.any() else None})
    for name in METHODS:
        if name == "equal":
            continue
        for metric in protocol["metrics"]:
            difference = bootstrap[name][metric] - bootstrap["equal"][metric]
            low, high = np.quantile(difference, [0.025, 0.975])
            rows.append({"candidate": name, "reference": "equal", "metric": metric,
                         "difference": profiles[name][metric]["value"] - profiles["equal"][metric]["value"],
                         "ci_low": float(low), "ci_high": float(high),
                         "interval_spans_zero": bool(low <= 0 <= high)})
    utility = continuous_utility(labels, probabilities["eeg"], probabilities["fmri"])
    positive = (utility > 0).astype(int)
    gate = {"positive_utility_records": int(positive.sum()), "records": int(labels.size)}
    for metric, operation in (("utility_auc", lambda ids: roc_auc_score(positive[ids], weights[ids])),
                              ("spearman_rho", lambda ids: spearmanr(utility[ids], weights[ids]).statistic)):
        all_ids = np.arange(labels.size)
        if np.unique(positive).size < 2 or np.ptp(weights) == 0 or np.ptp(utility) == 0:
            gate[metric] = {"value": None, "reason": "degenerate utility or weight"}
            continue
        samples = [operation(ids) for ids in indices if np.unique(positive[ids]).size == 2
                   and np.ptp(weights[ids]) > 0 and np.ptp(utility[ids]) > 0]
        low, high = np.quantile(samples, [0.025, 0.975])
        gate[metric] = {"value": float(operation(all_ids)), "ci_low": float(low), "ci_high": float(high),
                        "valid_resamples": len(samples)}
    gate_bins = []
    for low, high in zip(np.linspace(0, 1, 11)[:-1], np.linspace(0, 1, 11)[1:]):
        member = (weights >= low) & ((weights < high) if high < 1 else (weights <= high))
        if member.any():
            gate_bins.append({"weight_mean": float(weights[member].mean()), "utility_mean": float(utility[member].mean()),
                              "positive_utility_fraction": float(positive[member].mean()), "count": int(member.sum())})
    return {"records": int(labels.size), "profiles": profiles, "paired_differences": rows,
            "curves": curves, "confusion": confusion, "calibration": calibration,
            "gate_validity": gate, "gate_bins": gate_bins}


def run_benchmark(protocol=None):
    protocol = load_protocol() if protocol is None else protocol
    start = time.perf_counter()
    result, folds = {}, []
    with threadpool_limits(limits=1):
        pools = threadpool_info()
        for condition in protocol["quality_conditions"]:
            print(f"Benchmark condition: {condition}", flush=True)
            labels, probabilities, decisions, weights, strata = [], {n: [] for n in METHODS}, {n: [] for n in METHODS}, [], []
            for seed in protocol["fixture_seeds"]:
                y, p, d, w, report = nested_predictions(protocol, seed, condition)
                labels.append(y); weights.append(w); strata.extend([seed] * y.size); folds.extend(report)
                for name in METHODS:
                    probabilities[name].append(p[name]); decisions[name].append(d[name])
            result[condition] = summaries(protocol, np.concatenate(labels),
                {name: np.concatenate(p) for name, p in probabilities.items()},
                {name: np.concatenate(d) for name, d in decisions.items()}, np.array(strata), np.concatenate(weights))
    return {"protocol_id": protocol["protocol_id"], "protocol_sha256": PROTOCOL_HASH,
            "protocol_commit": PROTOCOL_COMMIT, "scope": protocol["scope"], "conditions": result,
            "folds": folds, "metadata": {"wall_seconds_including_uncertainty": time.perf_counter() - start,
            "platform": platform.system(), "machine": platform.machine(), "cpu": platform.processor() or "not reported",
            "python": platform.python_version(), "packages": {n: version(n) for n in ("numpy", "scipy", "scikit-learn", "threadpoolctl")},
            "threadpools": [{k: pool.get(k) for k in ("internal_api", "version", "num_threads", "architecture")} for pool in pools],
            "gpu_used": False, "source_sha256": {path.relative_to(ROOT).as_posix(): sha256_file(path)
                for path in [Path(__file__).resolve(), *sorted((ROOT / "src/neurofusion_qa").glob("*.py"))]}}}


def write_results(result):
    output = ROOT / "notebooks/artifacts/03_comparator_results.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(canonical_json(result) + "\n", encoding="utf-8")
    print(f"Saved {output.relative_to(ROOT).as_posix()}", flush=True)
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify-protocol", action="store_true")
    args = parser.parse_args()
    if args.verify_protocol:
        load_protocol()
        print(f"Frozen protocol verified: {PROTOCOL_COMMIT}, {PROTOCOL_HASH}")
    else:
        write_results(run_benchmark())
