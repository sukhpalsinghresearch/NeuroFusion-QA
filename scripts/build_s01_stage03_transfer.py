"""Build notebook/figure integration and a narrow, verified DGX source update.

Existing notebook sources are amended mechanically; original sources are hashed
independently of execution outputs so remote edits can be detected before update.
"""
import hashlib
import json
from pathlib import Path
import zipfile

import nbformat

ROOT = Path(__file__).resolve().parents[1]
NOTEBOOKS = ["00_S01_Environment_Boundary_Audit.ipynb", "01_S01_Synthetic_Feature_Contracts.ipynb", "02_S01_Provenance_End_to_End_Tutorial.ipynb"]
MARKER = "## Evidence-bound figure exports"


def main():
    directory = ROOT / "outputs/s01_dgx_transfer"
    directory.mkdir(parents=True, exist_ok=True)
    baseline = {}
    for index, name in enumerate(NOTEBOOKS):
        path = ROOT / "notebooks" / name
        notebook = nbformat.read(path, as_version=4)
        notebook.nbformat_minor = 5
        for i, cell in enumerate(notebook.cells):
            cell.setdefault('id', f's01-{index}-{i}')
        position = next((i for i,c in enumerate(notebook.cells) if c.source.startswith(MARKER)), len(notebook.cells))
        notebook.cells = notebook.cells[:position]
        baseline[f"notebooks/{name}"] = hashlib.sha256(json.dumps([c.source for c in notebook.cells], ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()
        notebook.cells += [nbformat.v4.new_markdown_cell(MARKER + "\n\nRegenerate relevant figures from this execution's evidence. Every family has editable SVG/PDF and 300 dpi PNG exports, a caption, and source hashes. [Full gallery](figures/README.md). Synthetic software evidence only."),
            nbformat.v4.new_code_cell(f"import sys\nfrom IPython.display import Markdown, display\nif str(ROOT / 'scripts') not in sys.path:\n    sys.path.insert(0, str(ROOT / 'scripts'))\nfrom s01_evidence_figures import generate\nfigure_records = generate('{index:02d}')\nfor item in figure_records:\n    display(Markdown(f\"### {{item['id']}}\\n\\n![{{item['id']}}](figures/{{item['id']}}.png)\\n\\n{{item['caption']}}\"))\n{{'figure_sets': len(figure_records), 'export_formats': ['png', 'svg', 'pdf']}}")]
        nbformat.validate(notebook)
        nbformat.write(notebook, path)
    nb = nbformat.v4.new_notebook(metadata={"kernelspec":{"display_name":"Python 3 (ipykernel)","language":"python","name":"python3"}})
    nb.cells = [nbformat.v4.new_markdown_cell("# 03 — Frozen controlled comparator benchmark\n\nQuestion: does label-free quality weighting improve held-out predictions when the quality signal is informative, irrelevant, or misleading?\n\nInputs: deterministic compact mathematical arrays, NOT the signal-derived EEG/fMRI features in 01/02. No protected data or E01 results. Outputs: aggregate 03 JSON evidence, all 12 metrics, paired intervals, calibration/confusion/gate diagnostics and editable figures. See [literature map](../docs/S01_LITERATURE_EVIDENCE_PLAN.md). No package from that map is claimed as an executed comparator."),
        nbformat.v4.new_code_cell("from pathlib import Path\nimport sys\nimport json\nfrom IPython.display import Markdown, display\nSTART = Path.cwd().resolve()\nROOT = next(p for p in (START, *START.parents) if (p / 'pyproject.toml').is_file())\nsys.path.insert(0, str(ROOT / 'scripts'))\nimport s01_comparator_benchmark as benchmark\nprotocol = benchmark.load_protocol()\n{'protocol_commit': benchmark.PROTOCOL_COMMIT, 'protocol_sha256': benchmark.PROTOCOL_HASH, 'settings': protocol}"),
        nbformat.v4.new_markdown_cell("## Matched, training-only comparison\n\nThree fixture seeds × 120 balanced records; two repetitions of four outer folds, three inner folds; all five comparators share unimodal predictions and eligible records. C, constant fusion weight and decision thresholds are selected on training OOF predictions. Quality scaling is fitted inside training folds without labels. Equal and negative outcomes remain in the report. Protocol was committed before first execution."),
        nbformat.v4.new_code_cell("results = benchmark.run_benchmark()\nresult_path = benchmark.write_results(results)\nassert len(results['folds']) == 72\nassert all(row['records'] == 360 for row in results['conditions'].values())\nassert all(len(row['profiles']) == 5 for row in results['conditions'].values())\n{'artifact': result_path.relative_to(ROOT).as_posix(), 'records_per_condition': 360, 'outer_fold_runs': 72, 'metrics': protocol['metrics'], 'wall_seconds': results['metadata']['wall_seconds_including_uncertainty']}"),
        nbformat.v4.new_markdown_cell("## Predeclared primary result and uncertainty boundary\n\nBrier is the primary score. Report paired candidate-minus-equal differences, including misleading quality. The 1,000 paired percentile bootstrap resamples preserve seed/class strata and resample each record once after averaging repeated predictions. Intervals are conditional on fitted models: not refitting uncertainty, independent-fold inference, population or clinical generalization. No multiplicity-adjusted significance claim. Log loss clips probabilities to [1e−6,1−1e−6]; ECE uses ten equal-width bins. Threshold metrics use repeated-fold majority decisions, ties positive; precision/F1/MCC are zero when undefined."),
        nbformat.v4.new_code_cell("for condition, row in results['conditions'].items():\n    difference = next(d for d in row['paired_differences'] if d['candidate'] == 'quality' and d['metric'] == 'brier_score')\n    print(condition, json.dumps(difference, sort_keys=True))\nprint('Gate diagnostics use held-out unimodal utility, independent of the gate.')\n{condition: row['gate_validity'] for condition, row in results['conditions'].items()}"),
        nbformat.v4.new_markdown_cell("## Full evidence figure gallery\n\nAll twelve metrics and all five methods are graphed, followed by ROC/PR, calibration with bin support, confusion counts, utility validity and training-only tuning traces. [Full captioned gallery](figures/README.md). PDF/SVG and exact evidence hashes accompany each PNG. Mathematical quality conditions are ablations, not cross-dataset validation."),
        nbformat.v4.new_code_cell("from s01_evidence_figures import generate\nfigure_records = generate('03')\nfor name in ('F07_paired_brier', 'F09_calibration_support', 'F11_gate_validity'):\n    item = next(r for r in figure_records if r['id'] == name)\n    display(Markdown(f\"### {name}\\n\\n![{name}](figures/{name}.png)\\n\\n{item['caption']}\"))\n{'figure_sets': len(figure_records), 'gallery': 'notebooks/figures/README.md'}"),
        nbformat.v4.new_markdown_cell("## Next gate\n\nNotebook 04 will add predeclared robustness, resource measurements and release evidence; it is not complete yet. A sixth notebook (05) is reserved for real cross-dataset validation only when two licensed compatible paired-modality datasets and an untouched-target protocol are available. No synthetic scenario is renamed as a dataset.")]
    nbformat.validate(nb)
    path03 = "notebooks/03_S01_Frozen_Comparator_Benchmark.ipynb"
    nbformat.write(nb, ROOT / path03)
    files = [*(f"notebooks/{n}" for n in NOTEBOOKS), path03,
        "scripts/s01_comparator_benchmark.py", "scripts/s01_evidence_figures.py",
        "tests/test_s01_benchmark.py", "config/s01_comparator_protocol.json",
        "docs/S01_LITERATURE_EVIDENCE_PLAN.md", "notebooks/README.md", "notebooks/NOTEBOOK_SPECIFICATION.md"]
    manifest = {"files":{}, "notebook_source_baseline":baseline}
    archive_path = directory / "S01_DGX_Stage03.zip"
    with zipfile.ZipFile(archive_path,"w",compression=zipfile.ZIP_DEFLATED) as archive:
        for name in files:
            content=(ROOT/name).read_bytes()
            manifest["files"][name]=hashlib.sha256(content).hexdigest()
            archive.writestr(name,content)
        archive.writestr("STAGE03_MANIFEST.json",json.dumps(manifest,indent=2))
    print(json.dumps({"files":len(files),"archive":archive_path.relative_to(ROOT).as_posix(),"sha256":hashlib.sha256(archive_path.read_bytes()).hexdigest()},indent=2))


if __name__ == "__main__":
    main()
