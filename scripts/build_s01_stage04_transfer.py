"""Narrow DGX update; excludes all private fonts and local execution artifacts."""
from pathlib import Path
import json
import zipfile
import nbformat
from neurofusion_qa.provenance import sha256_file, canonical_json

ROOT=Path(__file__).resolve().parents[1]


def build():
    notebook_paths=sorted((ROOT/'notebooks').glob('0[0-3]_S01_*.ipynb'))
    before={}
    for path in notebook_paths:
        nb=nbformat.read(path,as_version=4)
        before[path.relative_to(ROOT).as_posix()]=[cell.source for cell in nb.cells]
        for cell in nb.cells:
            cell.source=cell.source.replace('300 dpi PNG','1000 dpi Times New Roman PNG').replace('](figures/{name}.png)','](figures/previews/{name}.png)').replace('](figures/{item[\'id\']}.png)','](figures/previews/{item[\'id\']}.png)')
        nbformat.write(nb,path)
    nb=nbformat.v4.new_notebook()
    nb.metadata.kernelspec={'name':'neurofusion-s01','display_name':'Python (NeuroFusion S01)','language':'python'}
    nb.cells=[
        nbformat.v4.new_markdown_cell('# 04 — Interface robustness and evidence audit\n\nPermitted inputs: mathematical fixtures from frozen 03 only. No participant data, clinical claims or cross-dataset validation. Outputs: 38 Brier/interval sweep rows, nine measured CPU timing summaries, endpoint/failure contracts, two figure families, and a bounded claim ledger. The protocol was committed before a successful result execution. Each perturbation is applied per repeat before probability averaging.\n\nFigure contract: **Times New Roman, minimum 14-point native text, 1000 DPI PNG plus PDF/SVG**. Screen previews are 150 DPI, explicitly not submission rasters. A licensed project font is required; silent fallback is forbidden.'),
        nbformat.v4.new_code_cell("from pathlib import Path\nimport sys, json, subprocess\nfrom IPython.display import Markdown, display\nROOT=Path.cwd()\nif not (ROOT/'pyproject.toml').exists(): ROOT=ROOT.parent\nassert (ROOT/'pyproject.toml').exists()\nsys.path.insert(0,str(ROOT/'scripts'))\nfrom s01_robustness_audit import load_protocol, run_audit, write_audit, check_contracts\nprotocol=load_protocol()\ndisplay(protocol)"),
        nbformat.v4.new_markdown_cell('## Frozen perturbations and measured public-kernel timing\n\nAvailability masks are shared across methods. Both remove unavailable modalities; both-unavailable and zero reliability reject. Probability shrinkage is an interface transformation, not real signal noise. Record-bootstrap intervals are conditional on fitted models; no refitting, population inference, or multiple-comparison significance claim. CPU timings are medians/IQR over 15 measured calls after three warmups, not a full pipeline or peak-memory audit.'),
        nbformat.v4.new_code_cell("audit=run_audit(protocol)\npath=write_audit(audit)\nassert len(audit['sweeps'])==38 and len(audit['timings'])==9\nassert audit['base_matches_03'] and audit['deterministic_sweep_replay']\ndisplay(audit['contracts'],audit['timings'])"),
        nbformat.v4.new_markdown_cell('## Publication figure exports\n\nRead all captions in the [gallery](figures/README.md). Resize vector figures intentionally for the manuscript: native font size alone does not guarantee readability after shrinking a dense multi-panel figure.'),
        nbformat.v4.new_code_cell("from s01_evidence_figures import generate\nfigure_records=generate('04')\nfor item in figure_records:\n    display(Markdown(f\"### {item['id']}\\n\\n![Screen preview](figures/previews/{item['id']}.png)\\n\\n{item['caption']}\"))\n{'figure_sets':len(figure_records),'png_dpi':1000,'font':'Times New Roman'}"),
        nbformat.v4.new_markdown_cell('## Bounded evidence and release checks\n\nThese checks validate current source/artifact hashes and the aggregate-only boundary. They do not certify clean-install CI across all supported Python/OS combinations, license compatibility of later external datasets, clinical utility, or external validation. Those submission gates remain open.'),
        nbformat.v4.new_code_cell("checks={}\nfor name,args in [('evidence',['scripts/verify_s01_evidence.py']),('provenance',['scripts/s01_provenance_tutorial.py','--verify']),('release_boundary',['scripts/validate_release.py'])]:\n    completed=subprocess.run([sys.executable,*args],cwd=ROOT,check=True,text=True,capture_output=True)\n    checks[name]=completed.stdout.strip()\nledger={'scope':'synthetic_software_evidence_only','checks':checks,'supports':['frozen comparator and robustness protocols','availability endpoint and fail-closed contracts','1000 DPI Times New Roman exports with source hashes','runtime-specific CPU kernel timings'],'does_not_support':['clinical utility','real signal-noise robustness','cross-dataset generalization','peak native memory','all-platform clean-install CI certification']}\nfrom neurofusion_qa.provenance import canonical_json\n(ROOT/'notebooks/artifacts/04_claim_ledger.json').write_text(canonical_json(ledger)+'\\n',encoding='utf-8')\ndisplay(ledger)")]
    path=ROOT/'notebooks/04_S01_Interface_Robustness_Evidence_Audit.ipynb'
    nbformat.validate(nb); nbformat.write(nb,path)
    files=[*notebook_paths,path,ROOT/'config/s01_robustness_protocol.json',*[ROOT/name for name in ['scripts/s01_robustness_audit.py','scripts/s01_evidence_figures.py','scripts/verify_s01_evidence.py','tests/test_s01_robustness.py','tests/test_s01_figure_style.py']]]
    manifest={'files':{p.relative_to(ROOT).as_posix():sha256_file(p) for p in files},'existing_notebook_sources':before,'excluded':'private fonts, outputs, local result artifacts'}
    destination=ROOT/'outputs/S01_DGX_Stage04.zip'
    with zipfile.ZipFile(destination,'w',zipfile.ZIP_DEFLATED) as archive:
        for p in files: archive.write(p,p.relative_to(ROOT).as_posix())
        archive.writestr('STAGE04_TRANSFER_MANIFEST.json',canonical_json(manifest)+'\n')
    print(destination.name,sha256_file(destination),len(files),'files; no fonts')


if __name__=='__main__':build()
