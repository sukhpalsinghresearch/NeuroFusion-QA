"""Build a source-only DGX audit update without rewriting local notebooks.

Inspect the existing DGX job first. Compare notebook source cells with the
manifest baseline, back up destination files, then apply only this scoped update.
No Windows results, private fonts, environments or credentials are transferred.
"""
import hashlib
import json
from pathlib import Path
import zipfile

import nbformat

ROOT = Path(__file__).resolve().parents[1]
PRE_HARDENING_SHA256 = {
    'src/neurofusion_qa/gating.py': 'babdd3fa87c28e46ffb10cfb2e879028b396841a1e94c33289803a2040abd799',
    'src/neurofusion_qa/quality.py': 'bcb0f72e326ec80752f4b8d2606312fd89ec915b383a58006857a5997dca67c0',
    'src/neurofusion_qa/features.py': 'a465c03c2fdbec4f23551292a4256254d0aba2bac4c7ea46ba34095fcd81aefb',
}


def build():
    name = 'notebooks/04_S01_Interface_Robustness_Evidence_Audit.ipynb'
    notebook = nbformat.read(ROOT / name, as_version=4)
    code = [c.source for c in notebook.cells if c.cell_type == 'code']
    assert len(code) == 4 and 'from s01_release_evidence import run_release_audit' in code[-1]
    previous = code.copy()
    previous[-1] = code[-1].split('from s01_release_evidence import run_release_audit')[0] + 'display(ledger)'
    for cell in notebook.cells:
        if cell.cell_type == 'code':
            cell.execution_count = None
            cell.outputs = []
        cell.metadata.pop('execution', None)
    notebook.metadata.pop('execution_method', None)
    notebook.metadata.kernelspec = {'name': 'neurofusion-s01', 'display_name': 'Python (NeuroFusion S01)', 'language': 'python'}
    nbformat.validate(notebook)
    content = {name: nbformat.writes(notebook).encode('utf-8')}
    for relative in ['scripts/s01_release_evidence.py', 'scripts/run_s01_notebooks_inline.py',
                     'scripts/apply_s01_audit_update.py', 'tests/test_numerical_hardening.py',
                     'tests/test_s01_audit_transfer.py',
                     *PRE_HARDENING_SHA256,
                     'tests/test_s01_release_evidence.py', 'docs/S01_PROJECT_ALIGNMENT_AUDIT.md',
                     'notebooks/README.md', 'notebooks/NOTEBOOK_SPECIFICATION.md',
                     'notebooks/artifacts/README.md', 'scripts/S01_DGX_RUNBOOK.md']:
        content[relative] = (ROOT / relative).read_bytes()
    manifest = {'scope': 'source_only_no_local_results_or_private_fonts',
                'files': {p: hashlib.sha256(data).hexdigest() for p, data in content.items()},
                'expected_previous_04_code_cells': previous,
                'expected_previous_source_sha256': PRE_HARDENING_SHA256,
                'requires': 'existing verified stage04 source; inspect running job and back up before replacement',
                'does_not_certify': 'DGX installation or execution completion'}
    target = ROOT / 'outputs/S01_DGX_Audit_Update.zip'
    target.parent.mkdir(exist_ok=True)
    with zipfile.ZipFile(target, 'w', zipfile.ZIP_DEFLATED) as archive:
        for relative, data in content.items():
            archive.writestr(relative, data)
        archive.writestr('S01_AUDIT_TRANSFER_MANIFEST.json', json.dumps(manifest, indent=2) + '\n')
    print(target.name, hashlib.sha256(target.read_bytes()).hexdigest(), len(content), 'source files; not uploaded')


if __name__ == '__main__':
    build()
