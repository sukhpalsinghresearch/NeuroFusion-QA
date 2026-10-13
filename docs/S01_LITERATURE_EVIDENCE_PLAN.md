# Literature-informed evidence and figure plan

Revised 11 October 2026. This is a relevance map, not a claim to reproduce every experiment or a systematic review. The preparation corpus contains nine papers from 2023–2025. A paper's task-specific parameters are not automatically meaningful for another task.

12 October continuation: [the direct-comparator review](S01_DIRECT_COMPARATOR_REVIEW.md) adds six separately tracked primary records: direct EEG/fMRI classification candidates, general quality-aware multi-view candidates and one paired-modality task mismatch. It records read depth, settings/metrics, source inconsistencies, fair-comparison requirements and the still-closed real-data gate. These are literature candidates, not executed external baselines; the original nine software-inspiration papers remain a separate corpus.

## Source-to-evidence map

| Primary source | Evidence dimensions used or planned for S01 | Not imported as a fusion metric |
| --- | --- | --- |
| [Bidsme, 2023](https://doi.org/10.21105/joss.05575) | Explicit data/metadata interfaces; input organization and identity checks in 00/02; standards adapters only if exercised | BIDS conversion performance; BIDS compliance is not asserted by namespaced IDs |
| [DWIQC, 2025](https://joss.theoj.org/papers/10.21105/joss.06974.pdf) | Explicit QC report schema, failure reasons, integration boundary in 01/02/04 | Diffusion preprocessing/eddy metrics: no DWI input or pipeline here |
| [FieldTrip reproducescript, 2024](https://joss.theoj.org/papers/10.21105/joss.05566.pdf) | Input/configuration/source/environment/seed/output lineage; manifest verification and tamper failures in 02/04 | Arbitrary pipeline reproduction, authenticated execution, or equivalence to FieldTrip |
| [landmarker, 2025](https://imec-publications.be/bitstreams/f0bdac9a-a43a-41b4-b9eb-f919e3a1c754/download) | Modular architecture, runnable examples, declared task-specific evaluation, neutral scope comparison | Point error (mm), successful detection rates at mm thresholds, heatmap settings: no landmarks predicted |
| [MRIQC protocol, 2024 preprint](https://doi.org/10.1101/2024.10.21.619532) and [functional IQM documentation](https://mriqc.readthedocs.io/en/stable/iqms/bold.html) | QA versus human scientific QC, distribution/outlier views, predeclared criteria and failure bookkeeping | Image-level SNR/CNR, FBER/EFC, DVARS, FD, tSNR, GCOR/outlier/AFNI metrics require their real inputs and definitions; not fabricated from compact arrays |
| [MultiMedEval, 2024](https://proceedings.mlr.press/v250/royer24a.html) | Common interface, declared task/metric pairs, all-method result tables and scenario-level breakdown; appropriate binary classification metrics in 03 | BLEU, ROUGE, METEOR, RadGraph/RadCliQ/CheXbert and segmentation metrics: no text generation or segmentation task |
| [PET2BIDS, 2024](https://doi.org/10.21105/joss.06067) | Neutral interoperability/metadata positioning; potential adapters require actual implementation | PET conversion metrics; no PET support claimed |
| [SPM 25, 2025](https://doi.org/10.21105/joss.08103) | Release-specific scope, source revision and version alignment in 04 | Adoption, maturity, neuroimaging inference or historical results borrowed from SPM |
| [UnfoldMakie, 2025](https://joss.theoj.org/papers/10.21105/joss.07560.pdf) | Editable vector exports, perceptually ordered maps, separate measured generation timing and hardware context in 04 | Topoplot/animation speed comparisons or scalp geometry without electrode positions |

The benchmark uses our explicitly declared synthetic settings, not hyperparameters attributed to these unrelated systems. None of the nine packages is an executed predictive comparator. Direct baselines are EEG-only, fMRI-only, equal fusion, quality-aware fusion, and a training-tuned constant-weight late fusion rule. See the frozen protocol for exact definitions.

## Quantitative dimensions

Notebook 03: ROC-AUC, average precision, Brier score, log loss, accuracy, balanced accuracy, precision, sensitivity, specificity, F1, MCC, ten-bin ECE; confusion counts; ROC/PR points; calibration bin counts; paired method differences and 95% percentile bootstrap intervals; gate-utility AUC/Spearman; shared-fold C/weight/threshold traces. ECE is a binned diagnostic, not a proper score. Brier/log loss jointly reflect calibration and discrimination, not calibration alone. [Official metric definitions](https://scikit-learn.org/stable/modules/model_evaluation.html), [calibration guidance](https://scikit-learn.org/stable/modules/calibration.html).

Notebook 04 planned: computational failure matrix; missing-modality/degradation sweeps; quality-direction/permutation ablations; sample-size and class-imbalance sensitivity; configuration/hash tamper matrix; numeric portability and deterministic replay; isolated comparable kernel timing with warm-up/repeats; memory only with a method measuring native allocations; release artifact checks and an explicit claim-evidence ledger. No retrospective selection of flattering plots.

Current execution boundary: 04 implements the failure, availability/probability-interface, quality-ablation, replay, CPU timing and release-evidence sections. Real signal-corruption/refitting, sample-size/class-imbalance sensitivity and native peak memory remain unexecuted; the planning inventory above must not be read as completed evidence. Any further experiment needs a separate locked protocol.

## Figure inventory and placement

Figures use stable IDs; each export has a caption, producing function, evidence/source hashes, and PNG/PDF/SVG variants. Main-paper selection is smaller than the supplement gallery. No decorative radar chart or ungrounded brain map is needed.

| ID | Purpose | Notebook | Intended placement |
| --- | --- | --- | --- |
| F00 | Environment/boundary evidence card (not a platform-support badge) | 00 | Supplement |
| F01 | EEG spectral/features and fMRI connectivity/block summaries on mathematical inputs | 01 | Supplement |
| F02 | Seven scientific-QC boundaries and independent integrity/QC truth table | 01 | Main candidate |
| F03 | Robust training-only quality transformation and fusion-weight response | 01 | Main candidate |
| F04 | Namespaced pairing and lineage/fail-closed schematic | 02 | Main candidate |
| F05 | Tutorial shapes, training/test boundary, distinct failure outcomes | 02 | Supplement |
| F06 | Multi-metric comparator profiles with per-method 95% intervals | 03 | Main candidate |
| F07 | Paired Brier differences versus equal fusion across quality conditions | 03 | Main candidate |
| F08 | ROC and PR curves, all comparators and conditions | 03 | Supplement |
| F09 | Calibration curves with bin counts, not ECE alone | 03 | Main/supplement |
| F10 | Threshold-based confusion matrices and operating metrics | 03 | Supplement |
| F11 | Gate weight versus held-out utility; validity/association diagnostics | 03 | Supplement |
| F12 | Fold-level C/threshold/constant-weight selections and split accounting | 03 | Supplement |
| F13 | Robustness/degradation/missingness and quality ablation sweeps | 04 | Main/supplement |
| F14 | Runtime/memory context, failure matrix, evidence and release coverage | 04 | Supplement |
| F15 | Real cross-dataset transfer, per-dataset metrics/CIs and shift diagnostics | optional 05 | Only after data/protocol gate |

## Optional sixth notebook: real cross-dataset gate

User has authorized one extra notebook if useful. Reserve `05_S01_Cross_Dataset_External_Validation.ipynb`; do not populate fake results. Required before execution: at least two named licensed/public datasets with compatible paired modalities and labels; access terms checked; subject/session/site grouping available; preprocessing/atlas/sampling/feature definitions harmonized; source-only tuning/calibration; locked untouched target evaluation; grouped leave-site/dataset-out splits; separate within-dataset and transfer results; training-only harmonization; per-dataset and macro results, class/prevalence shifts, missingness, and dataset-aware paired uncertainty. External-data metrics must use real adapters and tools, not rename generated fixtures as datasets. A classifier on unrelated single-modality datasets cannot establish EEG/fMRI fusion transfer.

## Current completeness boundary

00–02 supply software-contract evidence. 03 adds controlled synthetic comparisons, not real cohort performance. The prior literature packet is a targeted preparation review and is not yet an exhaustive inventory of direct quality-aware EEG/fMRI fusion methods. A later direct-comparator review and public-data suitability check remain necessary before claims of field-wide coverage or cross-dataset generalization. Hosted CI, all-platform support, external use, release archive DOI, and author approvals cannot be replaced by figures.
