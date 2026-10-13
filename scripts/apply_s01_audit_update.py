"""Apply the narrowly scoped, hash-verified S01 source update from project root.

Never applies local results or private fonts. Existing changed files and all
aggregate artifacts/notebooks/figures are backed up first, without overwriting
an earlier backup. Run only after checking for an existing notebook job.
"""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile


def apply(archive, expected_sha256, root):
    root = root.resolve()
    assert (root / 'pyproject.toml').is_file(), 'run from the intended S01 project root'
    assert hashlib.sha256(archive.read_bytes()).hexdigest() == expected_sha256, 'transfer archive hash mismatch'
    with zipfile.ZipFile(archive) as stream:
        manifest = json.loads(stream.read('S01_AUDIT_TRANSFER_MANIFEST.json'))
        assert manifest['scope'] == 'source_only_no_local_results_or_private_fonts'
        content = {}
        for name, digest in manifest['files'].items():
            path = (root / name).resolve()
            assert not Path(name).is_absolute() and path.is_relative_to(root)
            assert name.startswith(('scripts/', 'src/neurofusion_qa/', 'tests/', 'docs/', 'notebooks/'))
            assert not name.startswith(('notebooks/figures/', 'outputs/'))
            assert name == 'notebooks/artifacts/README.md' or not name.startswith('notebooks/artifacts/')
            assert path.suffix in {'.py', '.ipynb', '.md'}
            data = stream.read(name)
            assert hashlib.sha256(data).hexdigest() == digest, 'payload hash mismatch: ' + name
            content[name] = data
        for name, digest in manifest['expected_previous_source_sha256'].items():
            assert hashlib.sha256((root / name).read_bytes()).hexdigest() == digest, 'changed DGX source: ' + name
        notebook_name = 'notebooks/04_S01_Interface_Robustness_Evidence_Audit.ipynb'
        existing = json.loads((root / notebook_name).read_text())
        sources = [''.join(c['source']) if isinstance(c['source'], list) else c['source']
                   for c in existing['cells'] if c['cell_type'] == 'code']
        assert sources == manifest['expected_previous_04_code_cells'], 'DGX notebook source differs from expected baseline'
        backup = root / 'outputs/s01_pre_hardening_backup.zip'
        paths = {root / name for name in content if (root / name).is_file()}
        paths.update(p for folder in ('notebooks/artifacts', 'notebooks/figures')
                     for p in (root / folder).rglob('*') if p.is_file())
        paths.update((root / 'notebooks').glob('0[0-4]_S01_*.ipynb'))
        report = root / 'outputs/s01_notebook_execution.json'
        if report.exists():
            paths.add(report)
        with zipfile.ZipFile(backup, 'x', zipfile.ZIP_DEFLATED) as saved:
            for path in sorted(paths):
                saved.write(path, path.relative_to(root).as_posix())
        for name, data in content.items():
            target = root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        assert all(hashlib.sha256((root / name).read_bytes()).hexdigest() == manifest['files'][name]
                   for name in content)
    print(f'Applied {len(content)} source files; verified all payload hashes; backup: {backup.name}; no result/font transfer')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', type=Path, required=True)
    parser.add_argument('--sha256', required=True)
    args = parser.parse_args()
    apply(args.archive, args.sha256, Path.cwd())
