# S01 core notebook specification

Version: 0.4, revised 11 October 2026
Scope: synthetic/public software evidence only  
Primary venue target: SoftwareX

## Design decision

The evidence workflow uses five notebooks. Closely related checks stay together so reviewers can follow one coherent path without navigating a large notebook collection. Unit-level edge cases still belong in `tests/`; notebooks explain and integrate the important contracts.

No notebook may access E01 participant-level material or present E01 findings as S01 novelty. Synthetic benchmarks do not establish clinical validity or population generalization.

## Global rules

- Run notebooks from the repository root in numeric order.
- Use deterministic synthetic inputs unless a later protocol names a public, licensed dataset.
- Default seeds: fixture `20260918`, classifier `1201`, bootstrap `20260816`.
- Fit scaling, thresholds, and models using training partitions only.
- Save compact JSON/CSV evidence under `notebooks/artifacts/`.
- Use repository-relative paths; do not save participant identifiers or raw array dumps.
- Retain unfavorable, equal, and inconclusive benchmark outcomes.
- Stop execution on violated invariants.
- Do not use values from `results/frozen_summary.json` as S01 analytical evidence. Notebook 00 may invoke the release validator, which checks only its boundary metadata.

## Notebook suite

### 00 — Environment and boundary audit

**File:** `00_S01_Environment_Boundary_Audit.ipynb`  
**Status:** implemented and executed

Purpose:

- record Python and dependency versions;
- hash the public protocol;
- verify the permitted data surface;
- run the fail-closed release validator;
- record seed policy and the explicit E01 boundary.

Primary artifact: `artifacts/00_preflight_report.json`.

This notebook supports environment and release-boundary claims. It does not establish the full platform matrix until CI is green.

### 01 — Synthetic core workflow and contracts

**Current file:** `01_S01_Synthetic_Feature_Contracts.ipynb`  
**Status:** implemented; 12 code cells. DGX 1000-DPI rerun passed; local sequential-Python rerun is recorded separately.

This notebook combines the former feature, QC, quality, fusion, and modelling notebooks into one continuous synthetic workflow:

1. Generate deterministic mathematical EEG and fMRI fixtures.
2. Verify EEG-33, Fisher-z connectivity, and fMRI-1440 shapes, finiteness, ordering, and hashes.
3. Demonstrate that computational integrity and scientific QC are independent gates.
4. Exercise every fMRI QC threshold at its pass/fail boundary.
5. Fit quality scaling on training rows only; test missingness, clipping, directions, and availability.
6. Verify equal and quality-aware fusion, normalized weights, probability bounds, and utility independence.
7. Build matched synthetic unimodal classifiers, training-only threshold selection, and repeated held-out prediction aggregation.
8. Trigger representative NaN, constant, shape, invalid-probability, and zero-quality failures.

Artifacts:

- `artifacts/01_feature_contracts.json` — already generated;
- `artifacts/01_core_workflow.json` — integrated QC/quality/fusion/model evidence;
- Pass/fail cases are embedded in `artifacts/01_core_workflow.json` alongside the checks they support.

The notebook supports software contract and conformance claims only. It does not assert biological realism.

### 02 — Provenance contract and end-to-end tutorial

**File:** `02_S01_Provenance_End_to_End_Tutorial.ipynb`  
**Status:** implemented and executed on DGX; 7 code cells, zero error outputs. Current test counts are recorded in `README.md`.

This notebook combines provenance verification with the reviewer-facing tutorial:

1. Create namespaced synthetic observation identities.
2. Enforce declared join cardinality.
3. Record input/configuration/software/environment/seed/output lineage.
4. Serialize and independently verify a canonical execution manifest.
5. Trigger duplicate, missing, many-to-many, namespace-collision, altered-configuration, stale-output, and tampered-hash failures.
6. Run the complete synthetic path from features through integrity, QC, quality, modelling, fusion, evaluation, and provenance.
7. Explain one integrity failure and one separate scientific-QC failure.

Artifacts:

- `artifacts/02_execution_manifest.json`;
- `artifacts/02_provenance_failures.json`;
- `artifacts/02_tutorial_summary.json`.

This notebook supplies the end-to-end tutorial and provenance/failure figure inputs.

### 03 — Frozen comparator benchmark

**File:** `03_S01_Frozen_Comparator_Benchmark.ipynb`  
**Status:** executed on DGX; four code cells, zero errors; protocol c4d0ca6

The benchmark remains one notebook, but its protocol is frozen as a separate committed artifact before result cells are executed.

Workflow:

1. Load and verify `config/s01_comparator_protocol.json` (commit c4d0ca6) and its committed SHA-256 hash.
2. Compare EEG-only, fMRI-only, equal fusion, quality-aware fusion, and one declared conventional late-fusion baseline.
3. Use identical eligible records, folds, hyperparameter rules, seeds, and repetitions.
4. Separate correctness/conformance checks from predictive metrics.
5. Report paired uncertainty and gate-validity measures.
6. Retain equal, worse, and inconclusive outcomes.
7. Record runtime and peak memory only for meaningfully comparable operations.

Artifacts:

- `../config/s01_comparator_protocol.json` — committed and hashed before benchmark execution;
- `artifacts/03_comparator_results.json` — aggregate metrics, paired intervals, curves, calibration/confusion counts, gate diagnostics, fold hashes and execution metadata;
- `figures/F06*` through `figures/F12*` — PNG/PDF/SVG exports, captions and evidence hashes.

No external package is named as a comparator unless its real public interface is executed reproducibly.

### 04 — Robustness, evidence export, and release audit

**File:** `04_S01_Interface_Robustness_Evidence_Audit.ipynb`  
**Status:** implemented, four code cells; local explicit non-kernel execution and current-source DGX Jupyter-kernel execution both pass with zero error outputs.

This final notebook consolidates the checks needed immediately before submission. These are acceptance requirements, not an assertion that every submission gate has passed:

1. Execute the full edge-case matrix: NaN/Inf, empty/constant inputs, extreme scaling, invalid probabilities, zero/negative quality, missing modalities, degenerate classes, duplicate identities, and seed replay.
2. Validate all artifacts and their schemas/hashes.
3. Generate neutral table/figure source files from machine-readable results.
4. Populate the claim-evidence ledger with command, release/commit, fixture/license, check, and boundary status.
5. Record contextual runtime/memory results without extrapolating beyond the measured environment.
6. Run tests, release validation, notebook execution checks, and package-artifact installation checks.
7. Produce final checksums and a release-audit report.

Artifacts:

- `artifacts/04_robustness_results.json` and `.csv` — 38 frozen prediction-interface sweep rows, not real signal-noise experiments;
- `artifacts/04_failure_matrix.csv`;
- `artifacts/04_performance_results.csv`;
- `artifacts/04_claim_evidence_ledger.csv`;
- `artifacts/04_release_audit.json`;
- `artifacts/SHA256SUMS.txt`;
- public figure/table source files.

The release audit independently reconciles 474 saved metric identities/ranges/paired differences and passes a 44-case representative failure matrix. Empty fusion input, overflow-safe quality normalization, infinite training-quality handling, and constant-input connectivity have been repaired and directly regression-tested. Local and DGX suites each pass 97 tests. All five notebooks were rerun locally via an explicit non-kernel fallback and independently on the current-source DGX Jupyter kernel (6/12/7/4/4 cells, zero errors). Current notebook/source hashes and 106 evidence checksums match; nominal comparator/fold/sweep/contract values and frozen protocols exactly match each environment's preserved pre-hardening snapshot. Current artifact/source validation is not a full formal JSON-schema suite or a clean-install/platform certification. The audit deliberately reports `submission_ready: false`; its generic kernel-verification requirement is satisfied separately by the current DGX execution report and hash check.

Fresh wheel installation, public CI/coverage, release DOI, complete API documentation and author/reviewer approvals remain submission gates. Native peak memory is unmeasured. Sample-size/class-imbalance sensitivity requires a separate frozen protocol before execution; it is not silently added to the existing 03/04 experiments. See `../docs/S01_PROJECT_ALIGNMENT_AUDIT.md` for the current requirement-to-evidence assessment.

## Stage gates

1. **Core gate:** notebooks 00-01 pass in clean supported environments.
2. **Provenance gate:** identity/manifest APIs and tests exist before notebook 02.
3. **Benchmark gate:** the comparator protocol artifact is committed and hashed before notebook 03 result execution.
4. **Submission gate:** notebook 04 verifies every paper-facing claim and release artifact.

## Paper mapping

| Paper evidence | Notebook source |
| --- | --- |
| Architecture and module responsibilities | 02 end-to-end tutorial |
| Provenance and fail-closed behavior | 02 |
| Synthetic tutorial outputs | 02 |
| Comparator results and uncertainty | 03 |
| Robustness, portability, tables, and claim ledger | 04 |

Five core notebooks remain the plan. The user authorized one optional sixth on 11 October 2026: `05_S01_Cross_Dataset_External_Validation.ipynb`, conditional on real compatible paired datasets and a locked transfer protocol. See `docs/S01_LITERATURE_EVIDENCE_PLAN.md`. Additional evidence normally becomes another section, test, or artifact.
