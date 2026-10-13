# S01 notebook execution plan

These notebooks are the executable evidence layer for the NeuroFusion-QA software paper. They use deterministic synthetic inputs unless a later protocol explicitly names a public, licensed dataset. They must never load E01 participant-level data or present E01 cohort results as S01 novelty.

## Execution contract

Run notebooks from the repository root in numeric order:

```bash
python -m pip install -e ".[test,notebooks,figures]"
python scripts/run_s01_notebooks.py --kernel python3
```

Every notebook must:

- declare its question, permitted inputs, outputs, seed, and expected assertions;
- use only public package APIs unless it is explicitly testing an internal contract;
- fail on violated invariants instead of silently continuing;
- write compact machine-readable evidence under `notebooks/artifacts/`;
- avoid absolute machine paths, participant identifiers, and protected derivatives;
- identify which paper claim and backlog acceptance criterion it supports;
- retain neutral or negative results.

## Five core notebooks, one conditional extension

| ID | Notebook | Purpose and principal evidence | Status |
| --- | --- | --- | --- |
| 00 | Environment & boundary audit | Versions, protocol hash, release validation, permitted inputs, and seed policy | Executed on DGX; 6 code cells, zero errors |
| 01 | Synthetic core workflow | Features, integrity versus QC, quality scaling, fusion, matched modelling, and representative failures | Executed on DGX; 12 code cells, zero errors |
| 02 | Provenance & end-to-end tutorial | Namespaced identity, checked joins, manifests, tamper failures, and the complete tutorial | Executed on DGX; 7 code cells, zero errors |
| 03 | Frozen comparator benchmark | Precommitted protocol, five fair comparators, three quality ablations, 12 metrics, paired 95% intervals and figures | Current-source DGX rerun: 4 code cells, zero errors |
| 04 | Interface robustness & evidence audit | Availability/weight perturbations, conditional intervals, measured CPU kernels, figures and bounded claim ledger | Current-source DGX rerun: 4 code cells, zero errors; 474 calculation checks and 44/44 requirements pass |
| 05 | Cross-dataset external validation (optional sixth) | Source-only tuning, untouched targets, grouped uncertainty and shift analysis | Authorized; requires compatible licensed real paired datasets |

The [literature evidence plan](../docs/S01_LITERATURE_EVIDENCE_PLAN.md) maps relevant paper dimensions to checks and figure families. Existing 00–02 gain figure sections; 03 adds a complete comparator gallery. See [figure gallery](figures/README.md). Unrelated task metrics are explicitly excluded, not fabricated.

## Publication figure contract

All current and future figure exports use **1000 DPI PNG and Times New Roman**, alongside embedded-font PDF and editable SVG. Native labels have a 14-point minimum; screen previews are separate 150 DPI files. The renderer fails if the exact font is unavailable. User-authorized private DGX font copies live under `outputs/.fonts`, outside release paths; do not redistribute them. Dense overview panels must be placed at a legible final size, split for manuscript layout when needed, or used as supplementary vector figures—not shrunk into an unreadable column.

Notebook 04 is a prediction-interface audit, not real signal-corruption, clinical, or cross-dataset validation. Its protocol applies perturbations before repeat averaging. CPU timing excludes input generation and is not a pipeline/GPU/peak-memory measurement. The claim ledger retains unverified clean-install/CI and external-validation gates.

Current local and DGX suites: 97 tests each; warnings are treated as errors. All five notebooks were refreshed locally at 6/12/7/4/4 code cells using explicitly labelled sequential Python execution, not a Jupyter kernel. The updated source was independently rerun on the DGX `neurofusion-s01` kernel at the same cell counts with zero errors; current notebook/source hashes and all 106 evidence checksums match. Exact pre/post nominal-evidence comparisons pass independently in both environments. The DGX run's unencrypted TCP kernel warning is recorded; this workflow uses synthetic/public data only, without changing transport/security settings.

The [project-alignment audit](../docs/S01_PROJECT_ALIGNMENT_AUDIT.md) reconciles 474 saved calculation checks. All 44 representative audit requirements now pass, including direct tests of the four repaired hardening gaps. Exact pre/post comparison confirms unchanged nominal metrics, folds, robustness sweeps and frozen protocols. Notebook 04 exports the failure matrix, performance/sweep CSVs, claim-evidence ledger, release-readiness JSON and checksums. Submission readiness remains false because the wider release gates remain open.

After ordered execution, verify evidence hashes and export manuscript-facing aggregate CSV tables:

```bash
python scripts/verify_s01_evidence.py
python scripts/s01_provenance_tutorial.py --verify
python scripts/validate_release.py
python scripts/s01_release_evidence.py
```

## Stage gates

1. **Core gate:** notebooks 00-01 pass in clean supported environments.
2. **Provenance gate:** the P0.3 public identity/manifest API exists before notebook 02.
3. **Benchmark gate:** notebook 03's protocol artifact is committed and hashed before result execution.
4. **Submission gate:** notebook 04 verifies every paper-facing claim and release artifact.

## Intended paper mapping

- Figure 1 architecture: notebook 02 plus the public module map.
- Figure 2 provenance/failure contract: notebook 02.
- Figure 3 tutorial outputs: notebook 02.
- Figure 4 comparator results: notebook 03.
- Optional portability/runtime figure and Tables 1-3: notebook 04.

Notebook outputs are software evidence, not a manuscript. Scientific interpretation remains bounded by the S01 publication plan in `../../Venue_Prep/S01_NeuroFusion_QA/`.
