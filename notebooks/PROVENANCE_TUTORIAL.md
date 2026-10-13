# S01 identity/provenance and signal-to-summary tutorial

From a clean checkout, using Python 3.10 or newer:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[test,notebooks]'
python -m pytest -W error
python scripts/s01_provenance_tutorial.py
python scripts/s01_provenance_tutorial.py --verify
python scripts/validate_release.py
```

On Windows, activate with `.venv\Scripts\Activate.ps1` instead. On the prepared DGX workspace, use `outputs/.venv` and notebook kernel `neurofusion-s01`; see `scripts/S01_DGX_RUNBOOK.md`.

The CLI and notebook 02 use the same implementation. An integration test executes it twice and checks deterministic summary equality. A passing local test is not a claim that hosted CI or the complete platform matrix has passed.

Expected output: 24 generated mathematical records; EEG feature matrix `[24, 33]`; fMRI feature matrix `[24, 1440]`; 16 training and 8 held-out records; 11 specific fail-closed provenance demonstrations. Saved files:

- `notebooks/artifacts/02_fixture_protocol.json`: declared fixture/model/split settings.
- `notebooks/artifacts/02_tutorial_summary.json`: shapes, hashes, checks, and demonstration-only evaluation profiles.
- `notebooks/artifacts/02_provenance_failures.json`: invalid conditions and diagnostics.
- `notebooks/artifacts/02_execution_manifest.json`: canonical lineage envelope and digest.

The summary does not contain raw signals or individual predictions. Recorded hashes identify the exact run; no preselected metric values or cross-platform bitwise equality are promised.

## Public API contract

`ObservationIdentity(namespace, subject, session, run, modality)` is immutable. Every component is a nonempty case-sensitive ASCII token. `to_dict()` serializes fields; `observation_key` excludes modality only, preserving the namespace/session/run for pairing. The API does not infer or verify real-world identity.

`checked_join(left, right, cardinality=...)` returns `(left_index, right_index)` pairs in left order. Both sides must be nonempty and cover the same observation keys. Full duplicate identities are always rejected. `one_to_one` requires unique keys on both sides; `many_to_one` permits distinct modalities sharing a left key but requires right-key uniqueness. Many-to-many, implicit dropping, unmatched namespaces, missing records, and extra records raise `ValueError`. Reordered inputs are explicitly aligned rather than rejected.

`canonical_json(payload)` and `canonical_json_sha256(payload)` use sorted keys, compact separators, finite JSON numbers, and significant array order. This convention is not RFC 8785. `sha256_file(path, chunk_size=...)` hashes bytes in positive-sized chunks; file-access errors are not suppressed.

`create_execution_manifest(root, derivative_id=..., inputs=..., outputs=..., configuration=..., software=..., environment=..., seed=...)` records ordered file hashes and detached metadata. Files must already exist; paths must be normalized root-relative POSIX paths with no traversal or escaped symlink. Input/output lists must be nonempty, unique, and disjoint. Software requires `name`, `version`, and `revision` (commit or explicit source hash); environment is a nonempty string-to-string version mapping; seed is a nonnegative integer. It returns `payload` plus `manifest_sha256` and writes nothing.

`verify_execution_manifest(manifest, root, expected_configuration=..., expected_manifest_sha256=None)` validates schema, payload/configuration digests, the caller's expected configuration, and all current files. It returns a detached payload. Changed/stale/missing files and invalid lineage raise `ValueError`. The optional trusted digest binds an independently retained snapshot; without it, a malicious rewrite of both payload and checksum cannot be detected. Reordering an ordered manifest input list changes its snapshot digest even though a checked identity join can safely align reordered rows.

## Scientific and security boundary

These are consistency guarantees, not authentication, execution attestation, biological realism, or clinical validation. QC/quality measurements are generated interface fixtures. The failed held-out fMRI QC fixture receives zero quality-aware weight; the equal-fusion branch is an interface demonstration that intentionally ignores this fixture, not a fair admissible-pipeline benchmark. Training decisions use training records only.

The source snapshot uses source hashes when no candidate commit/tag has been finalized. Existing release version 0.1.0 does not imply the released archive contains these uncommitted changes. A future release must bind this evidence to its exact candidate tag/archive. Do not introduce sensitive participant data into the DGX tutorial environment.
