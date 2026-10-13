# S01 project-alignment audit — 11 October 2026

The project is aligned with a **synthetic software-validation paper**, but is **not submission-ready**. Five core notebooks remain sufficient. No extra notebook was added for this audit. Notebook 05 remains conditional on compatible licensed paired real datasets and a locked transfer protocol.

12 October checkpoint: separate fresh Windows Python 3.12.14 and DGX Linux Python 3.13.9 wheel environments each pass 113 tests with warnings as errors and 90.24% package statement-plus-branch coverage. See [installation/CI evidence](INSTALLATION_AND_CI.md); the 97-test counts below describe the earlier hardening checkpoint. Full hosted CI is still unverified. The [six-record primary comparator review](S01_DIRECT_COMPARATOR_REVIEW.md) now separates direct-task candidates, general uncertainty methods and task mismatches, but does not claim exhaustive coverage or executed external baselines.

## Calculations and their boundaries

| Evidence | What is calculated | What is not established |
| --- | --- | --- |
| 01 feature/core contracts | EEG-33/fMRI-1440 construction, integrity versus QC, quality scaling, fusion, matched modelling and replay | Biological or clinical validation |
| 02 tutorial/manifest | Complete synthetic workflow, namespaced joins, lineage hashes and 11 provenance failures | Cryptographic authenticity or real cohort performance |
| 03 comparator | Five matched comparators, three quality conditions, 12 metrics, paired intervals, calibration/confusion and gate diagnostics | A signal-feature benchmark: classifiers instead use separate 6/8-dimensional mathematical inputs |
| 04 robustness | 38 availability/weight/probability-interface sweep rows | Real signal corruption, retraining robustness or cross-dataset transfer |
| 04 timing | Nine CPU kernel summaries; 3 warmups and 15 measured invocations per setting | GPU, full-pipeline or native peak-memory results; timing IQR is not a confidence interval |
| 04 release evidence | Failure matrix, CSV tables, claim ledger, calculation reconciliation and checksums | Approval of all submission requirements |

The frozen comparator uses identical records and splits across quality conditions. Hyperparameter, quality-scaler, constant-weight and threshold selection occur within outer training partitions. Repeated probabilities are averaged for probabilistic metrics; training-threshold decisions are majority-voted (ties positive) for binary metrics. These are distinct estimands and must be described separately.

Brier uses unmodified probabilities; log loss clips to `[1e-6, 1-1e-6]` under the frozen protocol. ECE uses ten uniform bins and empirical support. Average precision is the step-weighted PR summary, not trapezoidal PR area. The independent audit reconstructs ROC area, average precision, ECE and binary metrics from saved curves/counts, checks ranges and paired point differences: **474 checks pass**. Existing unit tests also compare metrics with scikit-learn and verify stratified-bootstrap replay/pairing.

The 1,000-resample intervals condition on fitted held-out predictions and preserve synthetic seed/class counts. They do not include model-refitting uncertainty, establish population generalization, or provide multiplicity-adjusted significance across all metrics. Absolute robustness intervals are not paired-difference significance tests. Three synthetic fixture seeds are not three real datasets.

Quality-aware fusion is not uniformly superior: informative quality helps the frozen synthetic Brier comparison, unrelated quality is inconclusive, and misleading quality is worse. Retain all three conditions and all five comparators. Gate utility is held-out absolute-error benefit; it is a diagnostic, not an input to the label-free gate.

## Hardening fixes verified locally and on DGX

The broader audit now passes all 44 representative requirements. The four gaps exposed by the previous audit have direct regression tests; the current local and DGX suites each pass 97 tests with warnings treated as errors (20.80 and 10.48 seconds respectively). This is representative coverage, not a claim that all possible invalid inputs have been tested.

| Case | Before hardening | Current behavior |
| --- | --- | --- |
| Empty fusion arrays | Returned an empty array | Explicit `ValueError`; also applied to soft fusion, utility and quality normalization |
| Equal quality masses of `1e308` | Sum overflowed; weight became 0 instead of 0.5 | Common factor-of-two rescaling prevents overflow and gives 0.5; nominal arithmetic is preserved |
| Infinite training-quality entry | Could yield NaN percentile scaling/transformation | Reject infinities during fitting; keep documented training-NaN imputation |
| Constant regional series | Connectivity returned NaN off-diagonal values | Reject undefined correlations; finite nonconstant inputs retain the original definition |

All five notebooks have been rerun locally (33 code cells) through the explicitly labelled non-kernel fallback. Source-bound tutorial/benchmark/robustness artifacts and 17 figure families were regenerated. The pre/post snapshot comparison confirms exact equality of comparator metrics, folds, robustness sweeps/contracts and protocol hashes; only the three intended public numerical source hashes changed. Timings are freshly measured and are not expected to match. No evidence hash was manually patched.

The updated source was independently rerun through the DGX `neurofusion-s01` Jupyter kernel: all five notebooks passed 6/12/7/4/4 code cells, zero error outputs. Saved notebook hashes, current public-source hashes and all 106 evidence checksums match. The DGX release audit independently passes 474 calculation checks and 44/44 requirements; its own preserved pre-hardening snapshot also gives exact nominal-evidence/protocol matches. Runtime-specific Windows evidence was not copied over DGX results. The release audit itself inspects saved notebook outputs conservatively; current kernel execution is separately established by `outputs/s01_notebook_execution.json` and this hash verification, not inferred from old outputs.

## Open requirements

- Complete the declared Python/OS and floor/newest hosted CI matrix. Fresh built-wheel tests and measured coverage are verified in the two environments above, not all 16 configured combinations.
- Complete API documentation, independent verification of feature definitions/units/ordering against the declared methods, maintenance/governance/support documents, and a release archive DOI.
- Author-approved venue declarations and independent S01/E01 claim-boundary review. No participant data were introduced by this audit.
- Extend the targeted direct-comparator review where needed: complete final-version/full-text/code/license extraction and preregister any executable external comparison. The nine software-inspiration papers and six added primary candidates are not an exhaustive review or reproduction. Do not import unrelated task metrics simply to increase the parameter count.
- Sample-size/class-imbalance sensitivity is proposed but unexecuted; freeze a separate protocol before experiments, rather than retrofitting 03/04 after seeing results.
- Real external validation requires named compatible paired datasets, licenses, grouping/harmonization and source-only tuning. Synthetic fixtures cannot substitute.
- DGX current-source execution is verified as above, but does not establish the full supported-platform matrix. The kernel reported unencrypted TCP transport; only synthetic/public inputs were used. Sensitive-data execution needs a separate secure-transport review; no transport or security settings were changed.
- The 17 figure families retain 1000-DPI PNG, Times New Roman and PDF/SVG. Final manuscript-size legibility still requires placement review: split dense panels or retain full-size/supplementary placement.

## Reproduction

Use the normal ordered Jupyter runner when a kernel is available. The explicitly labelled Python-only fallback supports trusted notebooks when local kernel startup is unavailable:

```bash
python scripts/run_s01_notebooks_inline.py
python -m pytest -W error
python scripts/s01_release_evidence.py
```

The fallback does not validate magics/widgets/kernel isolation. The audit writes the failure, performance, sweep and claim CSVs, `04_release_audit.json` and `SHA256SUMS.txt` under `notebooks/artifacts/`. An optional `--baseline` pre-hardening ZIP writes `04_hardening_regression.json` after exact nominal-evidence comparison. Checksums cover aggregate artifacts/figures, not private fonts, environments or notebooks that mutate during execution. `submission_ready: false` remains correct until the other release gates are closed.
