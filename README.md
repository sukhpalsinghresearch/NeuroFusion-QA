# NeuroFusion-QA

NeuroFusion-QA is a generalized, data-free reference implementation for separating four questions in multimodal biomedical fusion:

1. Does an observation pass scientific quality control?
2. Is its compact representation computationally valid?
3. How strongly should it contribute to a fused prediction?
4. Does the resulting subject-level weight track independently measured modality utility?

The repository accompanies the manuscript **“NeuroFusion-QA: Separating Signal Quality from Subject-Level Utility in EEG-fMRI Fusion.”** It contains the generalized feature equations, scientific-QC and computational-integrity checks, matched classifier construction, equal and quality-aware fusion, gate-validity targets, paired subject-level bootstrap evaluation, frozen aggregate development results, and publication-style figure-generation code.

## Scientific boundary

- All bundled results are aggregate summaries from the frozen 57-subject development cohort.
- No protected-subject identifiers, predictions, features, or quality records are included.
- The 11-subject protected cohort was not accessed for the reported analysis.
- A passing integrity check does not imply scientific QC approval.
- A fusion weight is not called reliability unless it passes an independent utility-validity test.

## Installation

```bash
python -m venv .venv
python -m pip install -e ".[test,figures]"
```

Alternatively, create the recorded cross-platform environment:

```bash
conda env create -f environment.yml
conda activate neurofusion-qa
```

## Minimal example

```python
import numpy as np
from neurofusion_qa.gating import equal_fusion, soft_fusion, continuous_utility

p_eeg = np.array([0.20, 0.65, 0.55])
p_fmri = np.array([0.35, 0.70, 0.40])
w_fmri = np.array([0.25, 0.80, 0.50])
y = np.array([0, 1, 1])

p_equal = equal_fusion(p_eeg, p_fmri)
p_soft = soft_fusion(p_eeg, p_fmri, w_fmri)
utility = continuous_utility(y, p_eeg, p_fmri)
```

## Reproduce the aggregate profile figure

```bash
python scripts/reproduce_summary_figures.py
python scripts/validate_release.py
```

This command reads only `results/frozen_summary.json` and writes outputs under `outputs/`. It cannot open imaging data or protected manifests.

## Repository layout

```text
config/                         frozen-protocol example
data/                           data-access boundary
docs/                           reproducibility and protected-cohort policy
results/frozen_summary.json     aggregate development evidence
scripts/                        aggregate-only reproduction script
src/neurofusion_qa/             features, QC, integrity, models, gates, evaluation
tests/                           unit tests for equations and safeguards
```

`docs/METHODS_TO_CODE.md` maps manuscript equations to functions, and `docs/RELEASE_BOUNDARY.md` records why private notebooks and participant-level artifacts are excluded.

## License and citation

The source code is released under the BSD 3-Clause License. Citation metadata are provided in `CITATION.cff`. Do not upload raw or derived participant-level files without confirming the source dataset terms and the study’s protected-cohort policy.
