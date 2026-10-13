# Manuscript-to-code map

This legacy map links the reusable implementation to the originating manuscript's numbered equations. Those equation numbers are not the S01 software-paper numbering, and do not imply that participant-level data or cohort results are S01 evidence.

| Manuscript item | Public implementation |
|---|---|
| EEG bandpower and 33-feature representation (Eq. 3) | `neurofusion_qa.features.eeg_features_33` |
| Fisher-z connectivity (Eq. 4) | `neurofusion_qa.features.fisher_connectivity` |
| 1440-element regional fMRI vector (Eq. 5) | `neurofusion_qa.features.fmri_features_1440` |
| Strict fMRI QC conjunction (Eq. 6; Table 2) | `neurofusion_qa.qc.evaluate_fmri_qc` |
| Computational integrity (Eq. 7) | `neurofusion_qa.integrity.validate_compact_features` |
| Matched logistic classifier (Eq. 8) | `neurofusion_qa.modeling.make_classifier` |
| Equal fusion (Eq. 9) | `neurofusion_qa.gating.equal_fusion` |
| Fold-specific robust quality scaling (Eq. 10) | `neurofusion_qa.quality.RobustQualityScaler` |
| Label-free reliability score (Eq. 11) | `neurofusion_qa.quality.reliability_score` |
| Quality/meta fusion (Eqs. 12 and 16) | `neurofusion_qa.gating.soft_fusion` |
| Binary and continuous utility (Eqs. 13 and 17) | `neurofusion_qa.gating.binary_utility`, `continuous_utility` |
| Aggregate metrics and paired intervals | `neurofusion_qa.evaluation` |

The raw AFNI and MNE workflows remain described in the originating manuscript and frozen protocol. Private participant notebooks are excluded. The five separate public S01 notebooks use synthetic fixtures and demonstrate software contracts; they are not copies of the participant analysis.

## S01 software-paper methods and evidence

| S01 responsibility | Implementation / driver | Regression or integration evidence |
| --- | --- | --- |
| Synthetic signal feature construction | `features.eeg_features_33`, `features.fisher_connectivity`, `features.fmri_features_1440`; `scripts/s01_core_workflow.py` | `tests/test_core.py`, `tests/test_numerical_hardening.py`, `tests/test_s01_workflow.py` |
| Separate compact integrity and supplied scientific QC | `integrity.validate_compact_features`, `qc.evaluate_fmri_qc` | `tests/test_core.py`, `tests/test_s01_workflow.py` |
| Training-fitted quality and availability | `quality.RobustQualityScaler`, `quality.reliability_score` | `tests/test_core.py`, `tests/test_numerical_hardening.py` |
| Equal/quality-weighted fusion and independent utility | `gating.equal_fusion`, `gating.label_free_quality_weight`, `gating.soft_fusion`, `gating.binary_utility`, `gating.continuous_utility` | `tests/test_core.py`, `tests/test_numerical_hardening.py`, `tests/test_evaluation_contracts.py` |
| Modelling, repeated predictions and training-only thresholds | `modeling.make_classifier`, `modeling.average_repeated_predictions`, `modeling.select_balanced_threshold` | `tests/test_core.py`, `tests/test_s01_benchmark.py` |
| Identity, joins, manifests and lineage | `provenance.ObservationIdentity`, `provenance.checked_join`, `provenance.create_execution_manifest`, `provenance.verify_execution_manifest` | `tests/test_provenance.py`, `tests/test_s01_tutorial.py` |
| Frozen five-method comparator and paired metric intervals | `scripts/s01_comparator_benchmark.py`; `config/s01_comparator_protocol.json` | `tests/test_s01_benchmark.py`; `notebooks/artifacts/03_comparator_results.json` |
| Interface sweeps, calculation reconciliation and failure matrix | `scripts/s01_robustness_audit.py`, `scripts/s01_release_evidence.py` | `tests/test_s01_robustness.py`, `tests/test_s01_release_evidence.py`; `notebooks/artifacts/04_release_audit.json` |
| Non-editable installed wheel parity and boundary | `scripts/check_wheel_install.py`, `scripts/validate_release.py` | `tests/test_wheel_install.py`, `tests/test_release_notebooks.py`; `docs/INSTALLATION_AND_CI.md` |

This responsibility map is not the complete API reference or an independent verification of every feature's scientific units/ordering. Those remain separate pre-submission checks. Benchmark inputs are six/eight-dimensional mathematical arrays, not the EEG-33/fMRI-1440 signal features. Frozen result scripts use explicit metric conventions; do not substitute the legacy evaluation helper's clipped-Brier convention for notebook 03's original-probability Brier.

