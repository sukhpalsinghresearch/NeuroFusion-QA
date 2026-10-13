# NeuroFusion-QA

NeuroFusion-QA is a generalized, data-free reference implementation for separating four questions in multimodal biomedical fusion:

1. Does an observation pass scientific quality control?
2. Is its compact representation computationally valid?
3. How strongly should it contribute to a fused prediction?
4. Does the resulting subject-level weight track independently measured modality utility?

The submission working tree supports the software article "NeuroFusion-QA: Explicit quality, integrity and provenance contracts for multimodal fusion workflows." Its five public notebooks use synthetic inputs. The historical implementation also accompanies the originating cohort manuscript, "NeuroFusion-QA: Separating Signal Quality from Subject-Level Utility in EEG-fMRI Fusion." Legacy aggregate cohort summaries are retained separately and are not new evidence for the software article.

See the [API reference](docs/API_REFERENCE.md), [installation and CI record](docs/INSTALLATION_AND_CI.md), [contribution guidance](CONTRIBUTING.md), [security guidance](SECURITY.md) and [changelog](CHANGELOG.md). Version 0.1.1 is the SoftwareX software snapshot; the historical v0.1.0 tag does not identify these contents. See the [release page](https://github.com/sukhpalsinghresearch/NeuroFusion-QA/releases/tag/v0.1.1) for downloadable source/distributions and the [quick start](docs/QUICKSTART.md). A software release is not evidence of journal acceptance or independent clinical validation.

## How the code supports the study

The public code package is intended for method inspection, testing, and aggregate-result reproduction. It provides:

- direct implementations of the manuscript's feature, QC, integrity, fusion, utility, and paired-evaluation equations;
- matched unimodal and fused modeling utilities that preserve the study's comparison rules;
- unit tests for numerical behavior and fail-closed safeguards;
- a frozen, aggregate-only result file and script for reproducing the released summary figure; and
- a methods-to-code map and automated audit of the public-release boundary.

The package does **not** reproduce participant-level preprocessing from redistributed data. Raw imaging data remain at the source repository, and private notebooks, participant-level derivatives, and the protected cohort are deliberately excluded. See [`docs/METHODS_TO_CODE.md`](docs/METHODS_TO_CODE.md) and [`docs/RELEASE_BOUNDARY.md`](docs/RELEASE_BOUNDARY.md) for the exact scope.

## Scientific boundary

- `results/frozen_summary.json` contains legacy aggregate summaries from the frozen 57-subject development cohort; it is not S01 analytical evidence. The separate S01 notebook artifacts are synthetic software-validation results.
- No protected-subject identifiers, predictions, features, or quality records are included.
- The 11-subject protected cohort was not accessed for the reported analysis.
- A passing integrity check does not imply scientific QC approval.
- A fusion weight is not called reliability unless it passes an independent utility-validity test.

## Installation

```bash
python -m venv .venv
```

Activate it with `.venv\Scripts\Activate.ps1` on Windows PowerShell or `source .venv/bin/activate` on Linux, then run `python -m pip install -e ".[test]"`. The test extra includes Matplotlib because the suite checks the publication-style contract. Rendering publication figures additionally requires a licensed Times New Roman installation; CI never substitutes or redistributes a font.

See [`docs/INSTALLATION_AND_CI.md`](docs/INSTALLATION_AND_CI.md) for non-editable wheel testing, dependency-floor sets, measured coverage and the distinction between configured CI and verified hosted runs. Python 3.10–3.13 on Linux/Windows is the targeted matrix, not a claim that every combination is already certified. Package metadata currently declares Python >=3.10; later Python versions and macOS are not validated here.

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

## Run the S01 synthetic evidence notebooks

The S01 notebook suite is a separate, synthetic-only software evidence track. It does not use the values in `results/frozen_summary.json` as analytical evidence or access any E01 participant-level material. Notebook 00 invokes the release validator, which checks only the file's scope and protected-access metadata.

```bash
python -m pip install -e ".[test,notebooks,figures]"
python scripts/run_s01_notebooks.py --kernel python3
```

See [`notebooks/README.md`](notebooks/README.md) for the ordered suite and [`notebooks/NOTEBOOK_SPECIFICATION.md`](notebooks/NOTEBOOK_SPECIFICATION.md) for exact inputs, artifacts, assertions, and claim boundaries.

The [direct-comparator review](docs/S01_DIRECT_COMPARATOR_REVIEW.md) maps six primary literature candidates to current metrics and remaining experiments. It distinguishes literature screening from executed baselines and explains why the real cross-dataset notebook remains conditional.

Notebook 02 and its standalone command exercise namespaced identities, checked joins, signal-to-feature-to-model integration, and independently verified execution manifests. See [`notebooks/PROVENANCE_TUTORIAL.md`](notebooks/PROVENANCE_TUTORIAL.md) for the public API contract, failure modes, and limits of hash-based provenance.

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

The source code is publicly released under the BSD 3-Clause License. If you use the implementation, equations, tests, or aggregate reproduction workflow, cite both the software release and the companion manuscript; machine-readable citation metadata are provided in `CITATION.cff`. Do not upload raw or derived participant-level files without confirming the source dataset terms and the study’s protected-cohort policy.
