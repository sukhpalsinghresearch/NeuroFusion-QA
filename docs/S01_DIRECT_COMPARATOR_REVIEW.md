# Direct fusion and quality-aware comparator review

Verified 12 October 2026. This is a targeted primary-source review, not a systematic review, reproduction, or assertion of novelty. It supplements the nine software-inspiration papers in [the evidence plan](S01_LITERATURE_EVIDENCE_PLAN.md). Six candidates are indexed in [`config/s01_literature_register.json`](../config/s01_literature_register.json). **None is an executed S01 comparator.**

## Search and screening boundary

Searches covered EEG/fMRI classification and quality/uncertainty-aware fusion, emphasizing 2023–2025 with one foundational 2021 method. Queries included `EEG fMRI multimodal fusion quality uncertainty classification 2023 2024 2025`, `simultaneous EEG fMRI fusion classification attention quality adaptive fusion paper`, and exact-title searches for trusted multi-view classification. The web search is not an exhaustive bibliographic database search; no PRISMA counts or completeness claim is made. Later 2026 work surfaced but was not incorporated into this previous-years extraction.

Eligible primary records must identify a fusion mechanism and evaluation task. Separate direct EEG/fMRI classification from general quality-aware multi-view methods and from other EEG/fMRI tasks. Review articles, EEG-only fusion, EEG–fNIRS, MRI–PET and fMRI–sMRI are not direct EEG/fMRI predictive comparators merely because their introductions mention EEG or fMRI.

Full-text selected sections were read for L01, L02 and L06. L03 is limited to its primary abstract; L04 to the proceedings abstract and indexed first page; L05 to the official proceedings abstract. Detailed optimization settings for L03–L05 remain unextracted, not assumed absent. OpenReview verification pages and some publisher fetches prevented full-text access; no authentication/security check was bypassed. Paper/data/code access and licenses remain distinct questions.

## Primary-source extraction

### L01 — MCSP (2024 preprint; 2025 journal listing)

Wei et al., *Multi-modal Cross-domain Self-supervised Pre-training for fMRI and EEG Fusion*. Extraction uses [arXiv v1](https://arxiv.org/html/2409.19130v1), sections 3.5, 4, 5.1 and tables 2–4; the [journal DOI](https://doi.org/10.1016/j.neunet.2024.107066) is a version-follow-up, not a claim to have checked final-text equivalence.

MCSP learns spatial, temporal and spectral representations with cross-domain/cross-modal self-supervision and distillation. Settings include Adam, 50 epochs, learning rate 0.0005, pretraining/fine-tuning batches 128/32, temperature 0.2 and cross-modal loss balance 0.8; evaluation describes ten runs of ten-fold CV. Classification tables report AUROC, accuracy, recall and precision. ADHD-200/ABIDE supply fMRI, not paired EEG/fMRI; EMBARC/HBN supply multimodal data. Same-subject runs are cross-matched for pretraining. EMBARC downstream text describes 265 patients, whereas the pretraining table lists 308 paired subjects: these are not interchangeable denominators.

S01 implication: separate modality coverage, pretraining and downstream cohorts, group repeated runs by participant, and report loss/domain ablations if reproducing this architecture. Its learned representation is not our QC gate. No numerical score comparison is valid on our synthetic fixtures.

### L02 — Same-task inner-speech fusion (2023)

Wilson et al., *Performance of data-driven inner speech decoding with same-task EEG-fMRI data fusion and bimodal models*. [Primary v1](https://arxiv.org/html/2306.10854v1), sections 2–4 and table 1.

Four participants perform eight-word classification using non-simultaneous same-task recordings. Subject-specific four-fold CV compares unimodal, early feature concatenation and late probability-vector stacking. Reported settings include linear SVM C=0.1, ANOVA top 1% fMRI/early-fusion features, top 2% EEG features and EEG random forests with 100 trees. Accuracy and fold standard deviations are reported; these are not paired 95% bootstrap intervals. The augmentation description creates additional within-label modality pairings, including test-set pairings. Such derived samples must not be treated as independent participants.

The results prose associates 44.96% with late fusion for one subject, while table 1 places 44.96% under augmented early fusion and 47.50% under late fusion. Preserve this unresolved discrepancy; do not choose a favorable value. This is not a population-level or simultaneous-recording comparator, and stacking is not our constant-weight late-fusion rule.

### L03 — Trusted Multi-View Classification (ICLR 2021)

Han et al., *Trusted Multi-View Classification*. [Primary author abstract and accepted-venue metadata](https://arxiv.org/abs/2102.02051).

TMC uses per-view evidence to parameterize Dirichlet class-probability distributions and combines views through Dempster–Shafer theory. Its uncertainty is model-derived, unlike S01's externally supplied label-free quality values. This is a methodological candidate, not an EEG/fMRI-specific reproduction. The accessible abstract supports accuracy/robustness/uncertainty motivation, not an extracted complete hyperparameter or calibration-metric inventory.

### L04 — Testing-time evidence filtering (CVPR 2025)

Liu, Chen and Yue, *Enhancing Testing-Time Robustness for Trusted Multi-View Classification in the Wild*. [Official proceedings record](https://openaccess.thecvf.com/content/CVPR2025/html/Liu_Enhancing_Testing-Time_Robustness_for_Trusted_Multi-View_Classification_in_the_Wild_CVPR_2025_paper.html), pp. 15508–15517; abstract and indexed first page.

The method detects unreliable evidence using a multiple-testing formulation and p-values, then down-weights it at testing time. It considers Belief Constraint, Aleatory Cumulative Belief and Averaging Belief Fusion. The introductory accuracy illustration replaces half the views to simulate sensor failure. This motivates actual corruption and evidence-conflict experiments, not a claim that our probability-interface sweeps reproduce them. Full algorithm thresholds, training/calibration partitions and complete tables require extraction before implementation. No EEG/fMRI validation is inferred from this record.

### L05 — Evolutionary trusted fusion (ICLR 2025)

Liang et al., *Trusted Multi-View Classification via Evolutionary Multi-View Fusion*. [Official proceedings abstract](https://proceedings.iclr.cc/paper_files/paper/2025/hash/7058bc192a37f5e5a57398887b05f6f6-Abstract-Conference.html).

TEF searches view/operator combinations to construct a pseudo-view and feeds its decision information back into individual views. The abstract describes evaluation across 13 multi-view datasets, emphasizing complex many-view settings. Architecture search is a different learning budget from two-view QC weighting. Search space, selection budget, splits and exact metrics remain unextracted here. The author-linked repository is a lead, not a reviewed, installed or license-approved dependency.

### L06 — CineBrain/CineSync (2025 preprint): task mismatch

*CineBrain: A Large-Scale Multi-Modal Brain Dataset During Naturalistic Audiovisual Narrative Processing*. [Primary v1](https://arxiv.org/html/2503.06940v1), sections 3 and 5.

Six participants supply simultaneous EEG/fMRI during audiovisual narratives; CineSync reconstructs video/audio rather than binary clinical labels. Video evaluation includes N-way retrieval, FVD, DTC/CTC, SSIM and PSNR; audio evaluation includes WER/CER, FAD, LSD/MCD and spectrogram SSIM/RMSE. The video setup uses AdamW, learning rate 1e-4, 50-epoch encoder pretraining and 5,000-step fine-tuning, with different GPU/batch budgets. These are not S01 classification metrics or a fair timing comparison. The v1 text promises public availability; current access, terms and stimulus rights were not verified. Paired modalities alone do not make it a suitable second binary-classification dataset.

## Requirement-to-evidence decisions

These decisions describe our current implementation, not properties attributed to the cited methods.

| Requirement | Present S01 evidence | Remaining action before a broader comparison |
| --- | --- | --- |
| Both unimodal and fusion controls | 03 has five matched methods | Add feature concatenation/OOF stacking only under a new predeclared protocol; do not relabel constant weighting as stacking |
| Comparable discrimination/operating metrics | 03 already has ROC-AUC, AP, accuracy, balanced accuracy, precision, sensitivity/specificity, F1 and MCC | Match task, label and averaging rule; AP is not automatically another paper's PR-AUC |
| Probabilities and uncertainty | 03 has original-probability Brier, clipped log loss, ECE and calibration counts | Learned uncertainty needs its own calibration/error/risk evaluation; QC weight is not calibrated uncertainty |
| Quality/utility distinction | Informative, unrelated and misleading conditions; held-out utility AUC/Spearman | Do not describe these conditions as evidence that real imaging QC predicts individual utility |
| Robustness | 04 covers availability and probability/weight interfaces | Raw-signal artifact injection, preprocessing and refitting remain unexecuted |
| Fair learning budget | Shared records/splits; training-only selection | External implementations need fixed versions, licenses, tuning/search budgets and out-of-fold meta-training |
| Uncertainty unit | Seed/class-stratified paired record bootstrap | Real repeated runs/trials require participant/site/dataset-aware grouping; report SD and CI distinctly |
| Compute | CPU API timing only | Same inputs, warm-up, training/inference boundary and measured native memory before speed claims |

No additional figure or notebook is needed just to show that a paper used a metric. Existing calibration, paired-difference, gate-diagnostic and failure figures cover the current estimands. New signal-corruption curves or learned-method leaderboards require new executed evidence, not cosmetic figure additions.

## External-data gate: still closed

EMBARC and HBN are leads from L01, not approved transfer datasets. In that paper EMBARC depression grading and HBN MDD diagnosis are different labels; a severity task cannot silently become a case/control task. iSpeech and CineBrain use different behavioral/reconstruction targets. None of these observations establishes two compatible licensed datasets for notebook 05.

Before access or execution: confirm source terms and secure handling, subject/session joins, modality availability, compatible labels/age/task/preprocessing definitions, training-only harmonization, grouped splits and an untouched target. Access authorization and ethics/consent constraints are not supplied by a paper's use of a dataset. No participant data were accessed by this review.

## Completion boundary and next decision

The targeted six-record screening and current-evidence mapping are complete; exhaustive direct-comparator coverage, final-version/code inspection and executable external baselines are not. S01 can currently claim synthetic software-contract evidence, not superiority to these methods or clinical/generalization validity. Keep 03/04 protocols and their negative/neutral outcomes frozen. Any new concatenation, OOF-stacking, learned-evidence or sample-size/imbalance experiment needs a separately locked protocol before result inspection; this review does not authorize a retrospective rewrite of 03/04.
