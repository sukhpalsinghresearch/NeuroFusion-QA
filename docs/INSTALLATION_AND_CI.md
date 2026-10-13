# Installation, wheel verification and CI

## Scope and current evidence

Release update, 13 October 2026: version 0.1.1 is the SoftwareX snapshot. Its newly built wheel passed 115 local Windows tests; all nine package modules retain the source-bound numerical bytes. The 11-12 October records below describe earlier 0.1.0 build validations. Read the exact 0.1.1 revision's GitHub Actions run for hosted results; a workflow configuration or local pass is not a hosted pass. Publishing code does not replace independent human reproduction or author approval of the paper.

The runtime contract remains Python >=3.10, NumPy >=1.24, SciPy >=1.10 and scikit-learn >=1.3. These are dependency declarations, not proof that every allowed combination works. The configured target is CPython 3.10–3.13 on Linux and Windows; macOS, later Python versions and the full hosted matrix remain unverified.

On 11 October 2026 a newly created, non-system-site-packages Windows Python 3.12.14 environment resolved the wheel's dependencies from PyPI and passed all 113 tests with warnings treated as errors. It used NumPy 2.5.4, SciPy 1.18.1, scikit-learn 1.9.1, Matplotlib 3.11.2 and pytest 9.1.1. Nine installed package files matched both the built wheel and current source exactly; the import was non-editable and outside the source checkout. This is separate from the earlier 97-test notebook environment and DGX kernel runs.

On 12 October 2026 the separate, fresh DGX Linux Python 3.13.9 wheel run was verified complete: **113 tests passed in 18.34 seconds**, warnings as errors, with **90.24% package statement-plus-branch coverage**. It independently resolved NumPy 2.5.4, SciPy 1.18.1, scikit-learn 1.9.1, Matplotlib 3.11.2 and pytest 9.1.1; dependency consistency, all nine installed-module hashes/non-editable origin, and the aggregate-only release boundary passed. The Linux wheel SHA-256 is `6ea423f6db82e6a48792c98339906eb7486a6814c345eb0dd0f9b846bd739f44`. The earlier pending-download status is superseded by this verified outcome, not by an assumed success or duplicate run.

The DGX notebook environment was not changed. All 106 existing aggregate/figure checksums and bound numerical/audit source hashes were rechecked, and all five notebook hashes still match their prior zero-error kernel report (6/12/7/4/4 code cells). This check is not a new notebook execution. Thirteen explicit Linux engineering reports are retained on DGX in `outputs/S01_DGX_WHEEL_EVIDENCE_20261012.zip`; no local download is claimed. Windows and DGX runtime evidence remain separate. These two actual environments do not certify the full 16-job matrix.

Measured package coverage, including branch opportunities, is **90.24%** (428 statements, 166 branches). The first measurement was 84.51% and exposed an untested gate-validity API. Direct pairwise-AUC, rank-correlation, paired-resample/replay and invalid-input tests raised coverage without changing numerical implementations or lowering the provisional 85% floor. This is not 100% path coverage, a formal scientific validation or an author-approved submission threshold. The coverage scope is `neurofusion_qa`, not all scripts/notebooks.

The 11-12 October validation did not itself commit, push, tag or publish code and did not establish a hosted green run. The 16-job matrix must run against the actual submitted source and retain a linkable result before claiming supported-platform certification.

## Fresh wheel installation

From the repository root, use a build environment and create a **new** test environment; do not reuse a prior editable install:

```bash
python -m pip install build
python -m build --outdir outputs/dist
python -m venv outputs/wheel-test
```

Activate the new environment (`outputs/wheel-test/Scripts/Activate.ps1` in PowerShell, or `source outputs/wheel-test/bin/activate` on Linux). Then:

```bash
python -m pip install "outputs/dist/neurofusion_qa-0.1.1-py3-none-any.whl[test]" coverage
python -m pip check
python -I scripts/check_wheel_install.py --wheel outputs/dist/neurofusion_qa-0.1.1-py3-none-any.whl
python -I -m coverage run -m pytest -W error
python -m coverage report
python -m coverage xml
python -m coverage html
python -I scripts/validate_release.py
```

Use the actual built filename when the package version changes. The check rejects checkout/editable imports, changed or missing package files, duplicate wheel members and unexpected wheel payloads. A passing origin/hash check alone does not prove a fresh environment: the caller must create it and resolve dependencies as above. Raw package-location paths remain in local diagnostic output only; the JSON verification report uses a bounded origin description.

The wheel contains nine package modules and distribution/license metadata, not participant data, notebooks, private fonts or environment files. The source archive additionally carries tests, protocols, scripts, documentation and aggregate fixtures needed by the test suite. It omits publication raster/vector exports and private fonts; reproduce figures from source in a licensed Times New Roman environment, or use the repository's separately verified figure gallery. Source-archive validation must not imply that omitted exports have been verified.

The Windows sandbox used during development blocked `ensurepip`/build temporary files. The fresh test environment was created without system packages, and the existing pip managed its interpreter using the documented `--python` option; approved build/install commands ran outside that sandbox. No global package configuration or numerical notebook environment was changed. This is a host-specific procedure, not a required package workaround. See the [pip interpreter-management documentation](https://pip.pypa.io/en/stable/topics/python-option/).

## Dependency policies

Each OS/Python job builds an sdist and wheel, installs the wheel (never an editable checkout), checks dependency consistency and import/code parity, executes the full suite including the synthetic signal-to-summary tutorial integration test, measures coverage and runs the aggregate-only release validator.

| Python | Floor policy: NumPy / SciPy / scikit-learn / Matplotlib / pytest |
| --- | --- |
| 3.10 | 1.24.0 / 1.10.0 / 1.3.0 / 3.8.0 / 8.0.0 |
| 3.11 | 1.24.0 / 1.10.0 / 1.3.0 / 3.8.0 / 8.0.0 |
| 3.12 | 1.26.0 / 1.11.2 / 1.3.2 / 3.8.0 / 8.0.0 |
| 3.13 | 2.1.0 / 1.14.1 / 1.6.0 / 3.9.2 / 8.3.3 |

The 3.10/3.11 jobs exercise declared lower bounds. Newer Python jobs use selected early wheel-compatible releases, not claimed absolute minimum versions; global minimum pins cannot be installed on every newer interpreter. The `newest` policy resolves the newest permitted available versions at execution time and is not a permanent lockfile. Transitive and engineering-tool versions are resolver-selected in both policies. Neither policy has yet been verified across all 16 combinations.

The floor sets also pin Pyparsing 3.1.4 because Matplotlib 3.8/3.9 use aliases that newer Pyparsing deprecates. The first hosted run exposed this during collection with warnings treated as errors. This is a transitive test-environment compatibility constraint, not suppression of the warnings gate or a numerical-source change. The newest jobs retain resolver-selected Pyparsing.

The workflow follows the [GitHub Python matrix/install/test guidance](https://docs.github.com/en/actions/tutorials/build-and-test-code/python) and [PyPA build guidance](https://packaging.python.org/en/latest/tutorials/packaging-projects/). Coverage uses an explicit package source scope and branch measurement as described in the [coverage configuration reference](https://coverage.readthedocs.io/en/latest/config.html).

## Boundaries and reports

- Workflow permissions are read-only; it does not publish packages, create releases or upload source archives.
- Only explicit engineering reports are uploaded: JUnit, coverage XML/HTML and the wheel-origin/hash JSON. No broad `outputs/` upload, environment or font archive is allowed.
- The suite tests figure-style settings and fail-closed font selection. It does not regenerate publication figures on hosted runners, where licensed Times New Roman is not guaranteed.
- Full frozen benchmarks and ordered notebook kernel execution are separate from these CI tests. Their protocols/results remain unchanged; historical kernel reports are not recertified as a new run.
- A passing release boundary scan does not mean `submission_ready: true`. Full CI, release DOI/maturity, complete API docs, author/independent approvals and real paired-dataset validation remain separate gates.

Current local reports are under ignored `outputs/`: `wheel_install_verification.json`, `wheel_junit.xml`, `coverage.xml` and `coverage.json`. Retain their actual wheel and source hashes when archiving a release; never copy Windows runtime reports over DGX evidence.
