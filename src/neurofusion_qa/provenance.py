"""Namespaced identities, explicit joins, and independently checked lineage.

Hashes establish consistency with a recorded snapshot, not authorship or
scientific validity. These helpers never authenticate a manifest signer.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path, PurePosixPath
from typing import Any


def sha256_file(path: str | Path, chunk_size: int = 1024 * 1024) -> str:
    if isinstance(chunk_size, bool) or not isinstance(chunk_size, int) or chunk_size <= 0:
        raise ValueError("chunk_size must be a positive integer")
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_json_sha256(payload: Any) -> str:
    encoded = canonical_json(payload).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def canonical_json(payload: Any) -> str:
    """Serialize finite JSON using sorted keys and compact separators.

    Array order is significant; object key order is not. Non-finite numbers
    are rejected. This is the package's JSON convention, not RFC 8785.
    """
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False)


@dataclass(frozen=True)
class ObservationIdentity:
    """An explicit namespace/subject/session/run/modality identity.

    Components are nonempty ASCII tokens (letters, digits, dot, underscore,
    hyphen). Values are case-sensitive and never inferred from a filename.
    """

    namespace: str
    subject: str
    session: str
    run: str
    modality: str

    def __post_init__(self) -> None:
        for name, value in asdict(self).items():
            if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", value):
                raise ValueError(f"identity {name} must be a nonempty ASCII token")

    @property
    def observation_key(self) -> tuple[str, str, str, str]:
        """Cross-modality join key; deliberately retains the namespace."""
        return self.namespace, self.subject, self.session, self.run

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


def checked_join(
    left: Sequence[ObservationIdentity], right: Sequence[ObservationIdentity],
    *, cardinality: str,
) -> list[tuple[int, int]]:
    """Return matched indices in left order, with no implicit row dropping.

    Supports ``one_to_one`` and ``many_to_one`` only. In many-to-one joins,
    distinct left modalities may share an observation, but complete duplicate
    identities remain invalid. Both sides must cover exactly the same keys.
    Raises ValueError for empty inputs, duplicates, missing/extra keys,
    unsupported cardinality, or an unmatched cross-namespace bare-ID collision.
    """
    if cardinality not in {"one_to_one", "many_to_one"}:
        raise ValueError("unsupported join cardinality; many-to-many joins are forbidden")
    if not left or not right:
        raise ValueError("join inputs must be nonempty")
    for label, identities in (("left", left), ("right", right)):
        if not all(isinstance(item, ObservationIdentity) for item in identities):
            raise ValueError(f"{label} join input requires ObservationIdentity values")
        if len(set(identities)) != len(identities):
            raise ValueError(f"duplicate {label} identity")
    left_keys = [item.observation_key for item in left]
    right_keys = [item.observation_key for item in right]
    if len(set(right_keys)) != len(right_keys):
        raise ValueError("right join cardinality violation: repeated observation key")
    if cardinality == "one_to_one" and len(set(left_keys)) != len(left_keys):
        raise ValueError("left join cardinality violation: repeated observation key")
    if set(left_keys) != set(right_keys):
        unmatched = set(left_keys) ^ set(right_keys)
        bare_namespaces: dict[tuple[str, str, str], set[str]] = {}
        for key in unmatched:
            bare_namespaces.setdefault(key[1:], set()).add(key[0])
        if any(len(namespaces) > 1 for namespaces in bare_namespaces.values()):
            raise ValueError("cross-namespace collision in unmatched observation keys")
        raise ValueError("missing or unexpected observation keys; join would drop records")
    lookup = {key: index for index, key in enumerate(right_keys)}
    return [(index, lookup[key]) for index, key in enumerate(left_keys)]


def _artifact_path(root: Path, relative: str) -> Path:
    if not isinstance(relative, str) or not relative or "\\" in relative or ":" in relative:
        raise ValueError("artifact path must be a normalized repository-relative POSIX path")
    path = PurePosixPath(relative)
    if path.is_absolute() or path.as_posix() != relative or any(part in {".", ".."} for part in path.parts):
        raise ValueError("artifact path must be a normalized repository-relative POSIX path")
    resolved = (root / relative).resolve()
    if not resolved.is_relative_to(root.resolve()):
        raise ValueError("artifact path escapes the declared root")
    if not resolved.is_file():
        raise ValueError(f"missing derivative or input artifact: {relative}")
    return resolved


def _fingerprints(root: Path, paths: Sequence[str]) -> list[dict[str, str]]:
    if isinstance(paths, (str, bytes)) or not paths:
        raise ValueError("artifact paths must be a nonempty sequence")
    if len(set(paths)) != len(paths):
        raise ValueError("duplicate artifact path")
    return [{"path": path, "sha256": sha256_file(_artifact_path(root, path))} for path in paths]


def create_execution_manifest(
    root: str | Path, *, derivative_id: str, inputs: Sequence[str], outputs: Sequence[str],
    configuration: Mapping[str, Any], software: Mapping[str, str],
    environment: Mapping[str, str], seed: int,
) -> dict[str, Any]:
    """Snapshot ordered input/output hashes and configuration/software lineage.

    Software must declare name, version, and revision (commit or source hash).
    Environment records caller-declared versions; it is not auto-detected.
    Paths are relative to root and cannot traverse outside it, even by symlink.
    All inputs and outputs must already exist; no files are modified.
    """
    if not isinstance(derivative_id, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", derivative_id):
        raise ValueError("derivative_id must be a nonempty ASCII token")
    if isinstance(seed, bool) or not isinstance(seed, int) or seed < 0:
        raise ValueError("seed must be a nonnegative integer")
    if not isinstance(configuration, Mapping):
        raise ValueError("configuration must be a JSON mapping")
    for name, metadata in (("software", software), ("environment", environment)):
        if not isinstance(metadata, Mapping) or not metadata or not all(
            isinstance(key, str) and isinstance(value, str) and key and value
            for key, value in metadata.items()
        ):
            raise ValueError(f"{name} must be a nonempty string-to-string mapping")
    if not {"name", "version", "revision"}.issubset(software):
        raise ValueError("software must declare name, version, and revision")
    root = Path(root)
    input_records = _fingerprints(root, inputs)
    output_records = _fingerprints(root, outputs)
    if set(inputs) & set(outputs):
        raise ValueError("input and output paths must be disjoint")
    payload = {
        "schema_version": "1.0", "derivative_id": derivative_id,
        "inputs": input_records, "outputs": output_records,
        "configuration": dict(configuration),
        "configuration_sha256": canonical_json_sha256(dict(configuration)),
        "software": dict(software), "environment": dict(environment), "seed": seed,
    }
    # Round-trip to detach mutable caller objects and reject non-JSON values.
    payload = json.loads(canonical_json(payload))
    return {"payload": payload, "manifest_sha256": canonical_json_sha256(payload)}


def verify_execution_manifest(
    manifest: Mapping[str, Any], root: str | Path, *,
    expected_configuration: Mapping[str, Any], expected_manifest_sha256: str | None = None,
) -> dict[str, Any]:
    """Verify schema, content hash, expected configuration, and current files.

    A separately trusted expected digest additionally binds the snapshot;
    without it, a party can rewrite both a payload and its digest. This function
    checks recorded lineage, not whether the recorded process actually ran.
    Returns a detached verified payload or raises ValueError with a diagnostic.
    """
    if not isinstance(manifest, Mapping) or set(manifest) != {"payload", "manifest_sha256"}:
        raise ValueError("invalid manifest envelope")
    payload = manifest["payload"]
    fields = {"schema_version", "derivative_id", "inputs", "outputs", "configuration",
              "configuration_sha256", "software", "environment", "seed"}
    if not isinstance(payload, dict) or set(payload) != fields or payload["schema_version"] != "1.0":
        raise ValueError("invalid manifest schema")
    digest = canonical_json_sha256(payload)
    if digest != manifest["manifest_sha256"]:
        raise ValueError("manifest content hash mismatch")
    if expected_manifest_sha256 is not None and digest != expected_manifest_sha256:
        raise ValueError("manifest differs from the trusted snapshot digest")
    if canonical_json_sha256(payload["configuration"]) != payload["configuration_sha256"]:
        raise ValueError("configuration hash mismatch")
    if canonical_json_sha256(dict(expected_configuration)) != payload["configuration_sha256"]:
        raise ValueError("configuration differs from the expected configuration")
    for label in ("inputs", "outputs"):
        records = payload[label]
        if not isinstance(records, list) or not records or not all(
            isinstance(record, dict) and set(record) == {"path", "sha256"}
            and isinstance(record["path"], str) and isinstance(record["sha256"], str)
            and re.fullmatch(r"[0-9a-f]{64}", record["sha256"])
            for record in records
        ):
            raise ValueError(f"invalid {label} artifact records")
    # Rebuild using the public constructor to independently validate all fields.
    current = create_execution_manifest(
        root, derivative_id=payload["derivative_id"],
        inputs=[row["path"] for row in payload["inputs"]],
        outputs=[row["path"] for row in payload["outputs"]],
        configuration=payload["configuration"], software=payload["software"],
        environment=payload["environment"], seed=payload["seed"],
    )["payload"]
    for label in ("inputs", "outputs"):
        for recorded, actual in zip(payload[label], current[label]):
            if recorded["sha256"] != actual["sha256"]:
                raise ValueError(f"{label} artifact hash mismatch (changed or stale): {recorded['path']}")
    return json.loads(canonical_json(payload))

