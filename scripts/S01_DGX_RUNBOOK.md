# S01 DGX workspace

Project folder: `Neurofusion EXT/S01_NeuroFusion_QA` in JupyterLab.  
Environment: `outputs/.venv` inside that folder.  
Kernel: `Python (NeuroFusion S01)` / `neurofusion-s01`.

The environment was created from DGX's bundled Miniconda Python. A first system-Python bootstrap could not install pip; its incomplete `.venv` directory is unused. Use `outputs/.venv` for this project.

From the project root:

```bash
source outputs/.venv/bin/activate
python -m pytest -W error
python scripts/run_s01_notebooks.py --kernel neurofusion-s01 --timeout 1200
python scripts/validate_release.py
```

The runner executes numbered notebooks in order, checks all code cells, saves their outputs, and writes `outputs/s01_notebook_execution.json`. Notebook evidence is stored under `notebooks/artifacts/`.

The initial source upload is `S01_DGX_Source.zip`, with per-file hashes in `TRANSFER_MANIFEST.json`. Execution changes notebook outputs and metadata; the manifest describes the uploaded source snapshot rather than the executed notebooks.

The S01 suite has five core notebooks, 00–04; a conditional sixth requires actual compatible licensed paired datasets. Current local and DGX suites each pass 97 tests (warnings as errors). The updated hardening/audit source passed the ordered DGX `neurofusion-s01` kernel run: 6/12/7/4/4 cells, zero errors. Current notebook/source hashes and 106 evidence checksums match. The final audit passes 474 calculation checks and 44/44 representative requirements; exact comparison against the saved DGX pre-hardening snapshot confirms unchanged nominal comparator metrics/folds, robustness sweeps/contracts and frozen protocols.

Publication font files are user-authorized private project copies under `outputs/.fonts`; `s01_evidence_figures.py` registers them per process. Do not include these font files or the private font-transfer archive in public releases. PNG exports are 1000 DPI; PDF embeds Times New Roman and SVG preserves text. Separate 150-DPI previews are for screen viewing only.

After reconnecting, inspect `outputs/stage04_notebooks.log`, `outputs/stage04_tests.log`, and `outputs/s01_notebook_execution.json` before starting another run. Check whether the prior runner is still active. Then independently verify:

```bash
python scripts/verify_s01_evidence.py
python scripts/s01_provenance_tutorial.py --verify
python scripts/validate_release.py
```

Expected complete figure evidence: 17 families / 51 PNG/PDF/SVG exports, plus 17 screen previews. Do not overwrite DGX runtime-specific artifacts with local Windows artifacts. Current logs are `outputs/hardening_tests.log`, `outputs/hardening_notebooks.log`, and `outputs/hardening_evidence.log`; the recoverable pre-update snapshot is `outputs/s01_pre_hardening_backup.zip`. The source update ZIP SHA-256 is `8f89b99e69493c64888d5b259cba7fbf8f676869f670adc0c03939335060a0c0`.

The kernel reports unencrypted TCP transport. This run used synthetic/public inputs only; sensitive-data execution requires a separate secure-transport review. No security/transport configuration was changed.

## Source-only calculation/release audit update

`python scripts/build_s01_audit_transfer.py` builds `outputs/S01_DGX_Audit_Update.zip`. Building it is not proof of upload or DGX execution. It strips notebook outputs and excludes fonts/local results. The scoped updater checks the archive/payload hashes, three pre-hardening public source hashes and notebook 04 code-cell baseline before making a recoverable backup and replacing source. Inspect existing DGX jobs first. Do not rerun the historical stage-04 builder: it regenerates an older notebook template and omits this audit section.

After the scoped update and normal ordered kernel execution, run:

```bash
python -m pytest -W error
python scripts/s01_release_evidence.py
```

Expected audit: 474 aggregate calculation checks, all 44 representative requirements passing, and `submission_ready: false`. After the ordered run, `python scripts/s01_release_evidence.py --baseline outputs/s01_pre_hardening_backup.zip` independently compares refreshed nominal metrics/folds/sweeps against the saved DGX snapshot. The audit is not a fresh wheel-install or supported-platform certification. Local sequential-Python fallback execution is explicitly labelled in metadata; prefer the normal DGX Jupyter kernel runner.

To independently verify notebook 02 evidence without regenerating it:

```bash
python scripts/s01_provenance_tutorial.py --verify
```
