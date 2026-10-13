"""Synthetic signal-to-summary tutorial and provenance failure demonstrations."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import platform
import tempfile
from dataclasses import replace
from importlib.metadata import version
from pathlib import Path

import numpy as np
from sklearn.model_selection import StratifiedKFold, train_test_split

from neurofusion_qa.evaluation import prediction_profile
from neurofusion_qa.features import eeg_features_33, fmri_features_1440
from neurofusion_qa.gating import (
    continuous_utility, equal_fusion, label_free_quality_weight, soft_fusion,
)
from neurofusion_qa.integrity import validate_compact_features
from neurofusion_qa.modeling import make_classifier, select_balanced_threshold
from neurofusion_qa.provenance import (
    ObservationIdentity, canonical_json, canonical_json_sha256, checked_join,
    create_execution_manifest, sha256_file, verify_execution_manifest,
)
from neurofusion_qa.qc import FmriQcMeasurements, evaluate_fmri_qc
from neurofusion_qa.quality import RobustQualityScaler, reliability_score


ROOT = Path(__file__).resolve().parents[1]
CONFIGURATION = {
    "scope": "synthetic_software_tutorial_not_benchmark",
    "fixture_seed": 20260918, "model_seed": 1201, "records": 24,
    "eeg_rate_hz": 250.0, "fmri_rate_hz": 1.25,
    "eeg_samples": 750, "fmri_samples": 128,
    "held_out_fraction": 1 / 3, "inner_folds": 3, "fixed_c": 0.1,
    "quality_directions": [1, -1, 1, -1],
    "threshold_source": "training_only_oof_predictions",
}


def array_digest(values: np.ndarray) -> str:
    canonical = np.ascontiguousarray(values, dtype="<f8")
    digest = hashlib.sha256(canonical_json(list(canonical.shape)).encode())
    digest.update(canonical.tobytes())
    return digest.hexdigest()


def run_signal_tutorial() -> dict:
    """Exercise real feature extraction through held-out fusion/evaluation.

    Inputs are generated signals, not observations of people. QC measurements
    and quality variables are explicitly synthetic interface fixtures. Their
    scientific meaning is not inferred from these generated signals.
    """
    config = CONFIGURATION
    rng = np.random.default_rng(config["fixture_seed"])
    labels = np.arange(config["records"]) % 2
    rng.shuffle(labels)
    eeg_rows, fmri_rows, signal_hashes = [], [], []
    t_eeg = np.arange(config["eeg_samples"]) / config["eeg_rate_hz"]
    t_fmri = np.arange(config["fmri_samples"]) / config["fmri_rate_hz"]
    for label in labels:
        # Deliberate mathematical class contrast, with no disease simulation.
        eeg = np.array([
            (1 + 0.15 * label + 0.03 * channel) * np.sin(2 * np.pi * (4 + channel) * t_eeg)
            + rng.normal(0, 0.3, t_eeg.size) for channel in range(8)
        ])
        latent = np.array([np.sin(2 * np.pi * 0.03 * t_fmri),
                           np.cos(2 * np.pi * 0.06 * t_fmri)])
        fmri = rng.normal(0, 0.6, (360, 2)) @ latent + rng.normal(0, 0.4 + 0.1 * label, (360, t_fmri.size))
        eeg_features = eeg_features_33(eeg, config["eeg_rate_hz"])
        fmri_features = fmri_features_1440(fmri, config["fmri_rate_hz"])
        assert validate_compact_features(eeg_features, (33,)).passed
        assert validate_compact_features(fmri_features, (1440,)).passed
        eeg_rows.append(eeg_features)
        fmri_rows.append(fmri_features)
        signal_hashes.append({"eeg": array_digest(eeg), "fmri": array_digest(fmri)})
    eeg_values, fmri_values = np.array(eeg_rows), np.array(fmri_rows)
    identities = [ObservationIdentity("s01-math", f"record-{index:03d}", "session-01", "run-01", "eeg")
                  for index in range(labels.size)]
    right_ids = [replace(identity, modality="fmri") for identity in reversed(identities)]
    pairs = checked_join(identities, right_ids, cardinality="one_to_one")
    # Actually use the checked indices to align a deliberately reversed matrix.
    aligned_fmri = fmri_values[::-1][[right for _, right in pairs]]
    np.testing.assert_array_equal(aligned_fmri, fmri_values)
    train, test = train_test_split(np.arange(labels.size), test_size=config["held_out_fraction"],
                                   stratify=labels, random_state=config["model_seed"])
    assert not np.intersect1d(train, test).size
    quality = rng.uniform(size=(labels.size, 4))
    quality[train[0], 1] = np.nan
    scaler = RobustQualityScaler.fit(quality[train])
    scaled = scaler.transform(quality[test])
    baseline = FmriQcMeasurements(0.1, 0.9, 2, 360, 360, True, 0.1)
    qc_reports = [evaluate_fmri_qc(baseline) for _ in test]
    qc_reports[0] = evaluate_fmri_qc(replace(baseline, censored_fraction=0.21))
    fmri_available = np.array([report.passed for report in qc_reports], dtype=int)
    q_eeg = reliability_score(scaled[:, :2], [1, -1])
    q_fmri = reliability_score(scaled[:, 2:], [1, -1], availability=fmri_available)
    weight = label_free_quality_weight(q_eeg, q_fmri)
    probabilities, model_reports = {}, {}
    inner = list(StratifiedKFold(config["inner_folds"], shuffle=True, random_state=config["model_seed"])
                 .split(eeg_values[train], labels[train]))
    for modality, values in (("eeg", eeg_values), ("fmri", aligned_fmri)):
        oof = np.full(train.size, np.nan)
        for fit, validation in inner:
            model = make_classifier(c=config["fixed_c"], seed=config["model_seed"])
            model.fit(values[train[fit]], labels[train[fit]])
            oof[validation] = model.predict_proba(values[train[validation]])[:, 1]
        threshold = select_balanced_threshold(labels[train], oof)
        model = make_classifier(c=config["fixed_c"], seed=config["model_seed"])
        model.fit(values[train], labels[train])
        probabilities[modality] = model.predict_proba(values[test])[:, 1]
        model_reports[modality] = {"fixed_c": config["fixed_c"], "training_oof_threshold": threshold,
                                  "features": values.shape[1], "fit_records": train.size}
    probabilities["equal"] = equal_fusion(probabilities["eeg"], probabilities["fmri"])
    probabilities["quality"] = soft_fusion(probabilities["eeg"], probabilities["fmri"], weight)
    assert weight[0] == 0
    assert probabilities["quality"][0] == probabilities["eeg"][0]
    utility = continuous_utility(labels[test], probabilities["eeg"], probabilities["fmri"])
    constant_failure = validate_compact_features(np.ones(33), (33,))
    assert not constant_failure.passed and not qc_reports[0].passed
    return {
        "scope": config["scope"], "clinical_claim_supported": False,
        "e01_data_accessed": False, "quality_measurements": "synthetic_interface_values",
        "records": int(labels.size), "training_records": int(train.size), "held_out_records": int(test.size),
        "eeg_shape": list(eeg_values.shape), "fmri_shape": list(fmri_values.shape),
        "identity_table_sha256": canonical_json_sha256([item.to_dict() for item in identities]),
        "input_signal_sha256": canonical_json_sha256(signal_hashes),
        "eeg_feature_sha256": array_digest(eeg_values), "fmri_feature_sha256": array_digest(fmri_values),
        "checked_join_reordered_inputs_correctly": True, "train_test_disjoint": True,
        "training_indices_sha256": canonical_json_sha256(train.tolist()),
        "held_out_indices_sha256": canonical_json_sha256(test.tolist()),
        "quality_fit_on_training_only": True, "shared_modality_splits": True,
        "model_reports": model_reports,
        "scientific_qc_fixture_failures": int(np.sum(fmri_available == 0)),
        "qc_rejected_modality_receives_zero_weight": True,
        "separate_integrity_failure": constant_failure.to_dict(),
        "qc_failure_with_intact_features": qc_reports[0].to_dict(),
        "profiles": {name: prediction_profile(labels[test], values) for name, values in probabilities.items()},
        "profiles_are_demonstration_only_not_benchmark": True,
        "prediction_sha256": {name: array_digest(values) for name, values in probabilities.items()},
        "continuous_utility_mean": float(utility.mean()),
    }


def provenance_failures(temp_parent: Path | None = None) -> list[dict]:
    """Trigger each documented failure in temporary synthetic files only."""
    failures = []

    def rejected(name, operation, diagnostic):
        try:
            operation()
        except ValueError as error:
            assert diagnostic in str(error), (name, str(error))
            failures.append({"case": name, "exception": "ValueError", "message": str(error)})
        else:
            raise AssertionError(f"Invalid provenance condition accepted: {name}")

    identity = ObservationIdentity("s01-math", "record-001", "session-01", "run-01", "eeg")
    rejected("duplicate_identity", lambda: checked_join([identity, identity], [identity], cardinality="one_to_one"), "duplicate left")
    rejected("missing_identity", lambda: checked_join([identity], [replace(identity, subject="record-002")], cardinality="one_to_one"), "missing or unexpected")
    rejected("namespace_collision", lambda: checked_join([identity], [replace(identity, namespace="other-math")], cardinality="one_to_one"), "cross-namespace")
    rejected("many_to_many", lambda: checked_join([identity], [identity], cardinality="many_to_many"), "many-to-many")
    scratch_root = Path(temp_parent) if temp_parent is not None else ROOT / "outputs"
    scratch_root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="s01-provenance-", dir=scratch_root) as directory:
        root = Path(directory)
        for name in ("a.json", "b.json", "result.json"):
            (root / name).write_text(canonical_json({"name": name}), encoding="utf-8")
        kwargs = dict(derivative_id="failure-fixture", inputs=["a.json", "b.json"], outputs=["result.json"],
                      configuration={"seed": 1}, software={"name": "test", "version": "1", "revision": "test"},
                      environment={"python": platform.python_version()}, seed=1)
        manifest = create_execution_manifest(root, **kwargs)
        verify = lambda candidate: verify_execution_manifest(candidate, root, expected_configuration={"seed": 1})
        reordered = create_execution_manifest(root, **{**kwargs, "inputs": ["b.json", "a.json"]})
        rejected("reordered_inputs", lambda: verify_execution_manifest(reordered, root, expected_configuration={"seed": 1},
                 expected_manifest_sha256=manifest["manifest_sha256"]), "trusted snapshot")
        rejected("altered_configuration", lambda: verify_execution_manifest(manifest, root, expected_configuration={"seed": 2}), "expected configuration")
        tampered = copy.deepcopy(manifest)
        tampered["payload"]["outputs"][0]["sha256"] = "0" * 64
        rejected("tampered_manifest", lambda: verify(tampered), "content hash mismatch")
        tampered["manifest_sha256"] = canonical_json_sha256(tampered["payload"])
        rejected("tampered_output_hash", lambda: verify(tampered), "outputs artifact hash mismatch")
        (root / "result.json").rename(root / "moved.json")
        rejected("missing_derivative", lambda: verify(manifest), "missing derivative")
        (root / "moved.json").rename(root / "result.json")
        (root / "result.json").write_text("stale", encoding="utf-8")
        rejected("stale_output", lambda: verify(manifest), "outputs artifact hash mismatch")
        (root / "a.json").write_text("changed input", encoding="utf-8")
        rejected("changed_input", lambda: verify(manifest), "inputs artifact hash mismatch")
    return failures


def write_evidence(summary: dict, failures: list[dict]) -> dict:
    """Write compact evidence and bind its actual files to public source hashes."""
    destination = ROOT / "notebooks" / "artifacts"
    destination.mkdir(parents=True, exist_ok=True)
    for filename, payload in (("02_tutorial_summary.json", summary),
                              ("02_provenance_failures.json", failures),
                              ("02_fixture_protocol.json", CONFIGURATION)):
        (destination / filename).write_text(canonical_json(payload) + "\n", encoding="utf-8")
    relative = lambda path: path.relative_to(ROOT).as_posix()
    source_paths = [Path(__file__).resolve(), *sorted((ROOT / "src" / "neurofusion_qa").glob("*.py"))]
    environment = {name: version(name) for name in ("numpy", "scipy", "scikit-learn", "neurofusion-qa")}
    environment["python"] = platform.python_version()
    manifest = create_execution_manifest(
        ROOT, derivative_id="s01-synthetic-end-to-end",
        inputs=[relative(destination / "02_fixture_protocol.json"), *[relative(path) for path in source_paths]],
        outputs=[relative(destination / name) for name in ("02_tutorial_summary.json", "02_provenance_failures.json")],
        configuration=CONFIGURATION,
        software={"name": "neurofusion-qa", "version": version("neurofusion-qa"),
                  "revision": "source-sha256-" + canonical_json_sha256({relative(path): sha256_file(path) for path in source_paths})},
        environment=environment, seed=CONFIGURATION["fixture_seed"],
    )
    path = destination / "02_execution_manifest.json"
    path.write_text(canonical_json(manifest) + "\n", encoding="utf-8")
    independently_loaded = json.loads(path.read_text(encoding="utf-8"))
    verify_execution_manifest(independently_loaded, ROOT, expected_configuration=CONFIGURATION,
                              expected_manifest_sha256=manifest["manifest_sha256"])
    return {"path": relative(path), "manifest_sha256": manifest["manifest_sha256"],
            "outputs_verified": len(manifest["payload"]["outputs"])}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true", help="Only independently verify saved evidence")
    args = parser.parse_args()
    if args.verify:
        manifest = json.loads((ROOT / "notebooks/artifacts/02_execution_manifest.json").read_text(encoding="utf-8"))
        verified = verify_execution_manifest(manifest, ROOT, expected_configuration=CONFIGURATION)
        print(f"Manifest verified: {len(verified['inputs'])} inputs, {len(verified['outputs'])} outputs")
    else:
        summary = run_signal_tutorial()
        failures = provenance_failures()
        print(json.dumps(write_evidence(summary, failures), indent=2))
        print(f"Tutorial passed: {summary['records']} mathematical records; {len(failures)} fail-closed cases")


if __name__ == "__main__":
    main()
