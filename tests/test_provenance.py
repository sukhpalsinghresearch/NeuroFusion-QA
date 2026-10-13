import copy
import json

import pytest

from neurofusion_qa.provenance import (
    ObservationIdentity, canonical_json, canonical_json_sha256, checked_join,
    create_execution_manifest, sha256_file, verify_execution_manifest,
)


def identity(subject="record-001", namespace="synthetic-a", modality="eeg"):
    return ObservationIdentity(namespace, subject, "session-01", "run-01", modality)


def test_namespaced_join_reorders_without_bare_id_matching():
    left = [identity(), identity("record-002"), identity(namespace="synthetic-b")]
    right = [identity(namespace="synthetic-b", modality="fmri"),
             identity(modality="fmri"), identity("record-002", modality="fmri")]
    assert checked_join(left, right, cardinality="one_to_one") == [(0, 1), (1, 2), (2, 0)]
    assert identity().to_dict()["namespace"] == "synthetic-a"


@pytest.mark.parametrize("changes", [{"namespace": ""}, {"subject": "bare/id"}, {"session": None}])
def test_invalid_identity(changes):
    fields = identity().to_dict()
    fields.update(changes)
    with pytest.raises(ValueError, match="identity"):
        ObservationIdentity(**fields)


@pytest.mark.parametrize("left,right,cardinality,diagnostic", [
    ([identity(), identity()], [identity()], "one_to_one", "duplicate left"),
    ([identity()], [identity(), identity()], "one_to_one", "duplicate right"),
    ([identity(), identity(modality="fmri")], [identity()], "one_to_one", "left join cardinality"),
    ([identity()], [identity(), identity(modality="fmri")], "many_to_one", "right join cardinality"),
    ([identity()], [identity("record-002")], "one_to_one", "missing or unexpected"),
    ([identity()], [identity(namespace="synthetic-b")], "one_to_one", "cross-namespace"),
    ([identity()], [identity()], "many_to_many", "many-to-many"),
    ([], [identity()], "one_to_one", "nonempty"),
])
def test_join_failures(left, right, cardinality, diagnostic):
    with pytest.raises(ValueError, match=diagnostic):
        checked_join(left, right, cardinality=cardinality)


def test_explicit_many_to_one():
    assert checked_join([identity(), identity(modality="fmri")], [identity(modality="label")],
                        cardinality="many_to_one") == [(0, 0), (1, 0)]


@pytest.fixture
def snapshot(tmp_path):
    for name in ("input-a.json", "input-b.json", "output.json"):
        (tmp_path / name).write_text(json.dumps({"artifact": name}), encoding="utf-8")
    config = {"c": 0.1, "nested": {"seed": 1201}}
    kwargs = dict(derivative_id="synthetic-tutorial", inputs=["input-a.json", "input-b.json"],
                  outputs=["output.json"], configuration=config,
                  software={"name": "neurofusion-qa", "version": "0.1.0", "revision": "test-snapshot"},
                  environment={"python": "test"}, seed=1201)
    return tmp_path, config, kwargs, create_execution_manifest(tmp_path, **kwargs)


def test_manifest_roundtrip_and_detachment(snapshot):
    root, config, kwargs, manifest = snapshot
    assert create_execution_manifest(root, **kwargs) == manifest
    restored = json.loads(canonical_json(manifest))
    assert verify_execution_manifest(restored, root, expected_configuration=config) == manifest["payload"]
    config["nested"]["seed"] = 2
    assert manifest["payload"]["configuration"]["nested"]["seed"] == 1201
    assert canonical_json_sha256({"a": 1, "b": 2}) == canonical_json_sha256({"b": 2, "a": 1})


def test_reordered_inputs_are_bound_by_trusted_digest(snapshot):
    root, config, kwargs, manifest = snapshot
    kwargs["inputs"] = list(reversed(kwargs["inputs"]))
    reordered = create_execution_manifest(root, **kwargs)
    assert reordered["manifest_sha256"] != manifest["manifest_sha256"]
    with pytest.raises(ValueError, match="trusted snapshot"):
        verify_execution_manifest(reordered, root, expected_configuration=config,
                                  expected_manifest_sha256=manifest["manifest_sha256"])


@pytest.mark.parametrize("target", ["input-a.json", "output.json"])
def test_changed_or_stale_artifact(snapshot, target):
    root, config, _, manifest = snapshot
    (root / target).write_text("changed", encoding="utf-8")
    with pytest.raises(ValueError, match="artifact hash mismatch"):
        verify_execution_manifest(manifest, root, expected_configuration=config)


def test_missing_derivative(snapshot):
    root, config, _, manifest = snapshot
    (root / "output.json").rename(root / "moved-output.json")
    with pytest.raises(ValueError, match="missing derivative"):
        verify_execution_manifest(manifest, root, expected_configuration=config)


def test_altered_configuration(snapshot):
    root, config, _, manifest = snapshot
    with pytest.raises(ValueError, match="expected configuration"):
        verify_execution_manifest(manifest, root, expected_configuration={**config, "c": 10})
    altered = copy.deepcopy(manifest)
    altered["payload"]["configuration"]["c"] = 10
    altered["manifest_sha256"] = canonical_json_sha256(altered["payload"])
    with pytest.raises(ValueError, match="configuration hash mismatch"):
        verify_execution_manifest(altered, root, expected_configuration=config)


def test_tampered_manifest_and_hash(snapshot):
    root, config, _, manifest = snapshot
    altered = copy.deepcopy(manifest)
    altered["payload"]["seed"] = 2
    with pytest.raises(ValueError, match="content hash mismatch"):
        verify_execution_manifest(altered, root, expected_configuration=config)
    altered = copy.deepcopy(manifest)
    altered["payload"]["outputs"][0]["sha256"] = "0" * 64
    altered["manifest_sha256"] = canonical_json_sha256(altered["payload"])
    with pytest.raises(ValueError, match="outputs artifact hash mismatch"):
        verify_execution_manifest(altered, root, expected_configuration=config)


@pytest.mark.parametrize("path", ["../escape.json", "/absolute.json", "a\\b.json", "a/./b.json"])
def test_unsafe_paths(snapshot, path):
    root, _, kwargs, _ = snapshot
    kwargs["inputs"] = [path]
    with pytest.raises(ValueError, match="repository-relative"):
        create_execution_manifest(root, **kwargs)


def test_duplicate_paths_and_nonfinite_configuration(snapshot):
    root, _, kwargs, _ = snapshot
    kwargs["inputs"] = ["input-a.json", "input-a.json"]
    with pytest.raises(ValueError, match="duplicate artifact"):
        create_execution_manifest(root, **kwargs)
    kwargs["inputs"] = ["input-a.json"]
    kwargs["configuration"] = {"bad": float("nan")}
    with pytest.raises(ValueError):
        create_execution_manifest(root, **kwargs)
    with pytest.raises(ValueError, match="positive integer"):
        sha256_file(root / "input-a.json", chunk_size=0)


def test_schema_and_metadata_fail_closed(snapshot):
    root, config, kwargs, manifest = snapshot
    with pytest.raises(ValueError, match="envelope"):
        verify_execution_manifest({}, root, expected_configuration=config)
    altered = copy.deepcopy(manifest)
    altered["payload"]["schema_version"] = "unknown"
    with pytest.raises(ValueError, match="schema"):
        verify_execution_manifest(altered, root, expected_configuration=config)
    kwargs["software"] = {"name": "test"}
    with pytest.raises(ValueError, match="revision"):
        create_execution_manifest(root, **kwargs)
