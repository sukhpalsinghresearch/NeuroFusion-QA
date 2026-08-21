# Manuscript-to-code map

This map links the reusable public implementation to the numbered equations in the companion manuscript. It does not imply that participant-level data are included.

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

The raw AFNI and MNE workflows remain described in the manuscript and frozen protocol. The release excludes copied notebooks because they contain machine-specific execution history and are not a safe or portable software interface.

