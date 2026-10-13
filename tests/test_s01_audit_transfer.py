"""Scoped updater rejects stale sources and preserves a recoverable snapshot."""
import hashlib
import json
from pathlib import Path
import sys
import zipfile

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from apply_s01_audit_update import apply


@pytest.fixture
def update(tmp_path):
    (tmp_path / 'pyproject.toml').write_text('[project]\nname="fixture"', encoding='utf-8')
    for directory in ('outputs/.fonts', 'src/neurofusion_qa', 'notebooks/artifacts', 'notebooks/figures'):
        (tmp_path / directory).mkdir(parents=True)
    source = 'src/neurofusion_qa/gating.py'
    (tmp_path / source).write_bytes(b'old source')
    name = 'notebooks/04_S01_Interface_Robustness_Evidence_Audit.ipynb'
    notebook = {'cells': [{'cell_type': 'code', 'source': ['print(1)'], 'outputs': [], 'execution_count': 1}]}
    (tmp_path / name).write_text(json.dumps(notebook), encoding='utf-8')
    (tmp_path / 'outputs/.fonts/private.ttf').write_bytes(b'private font fixture')
    (tmp_path / 'notebooks/artifacts/result.json').write_text('{}', encoding='utf-8')
    content = {source: b'new source', name: json.dumps(notebook).encode()}
    manifest = {'scope': 'source_only_no_local_results_or_private_fonts',
        'files': {key: hashlib.sha256(value).hexdigest() for key, value in content.items()},
        'expected_previous_source_sha256': {source: hashlib.sha256(b'old source').hexdigest()},
        'expected_previous_04_code_cells': ['print(1)']}
    archive = tmp_path / 'outputs/update.zip'
    with zipfile.ZipFile(archive, 'w') as stream:
        for key, value in content.items():
            stream.writestr(key, value)
        stream.writestr('S01_AUDIT_TRANSFER_MANIFEST.json', json.dumps(manifest))
    return tmp_path, archive, hashlib.sha256(archive.read_bytes()).hexdigest(), source


def test_scoped_update_backs_up_existing_evidence_without_fonts(update):
    root, archive, digest, source = update
    apply(archive, digest, root)
    assert (root / source).read_bytes() == b'new source'
    with zipfile.ZipFile(root / 'outputs/s01_pre_hardening_backup.zip') as saved:
        assert saved.read(source) == b'old source'
        assert 'notebooks/artifacts/result.json' in saved.namelist()
        assert not any(name.endswith('.ttf') for name in saved.namelist())


def test_stale_destination_fails_before_any_write(update):
    root, archive, digest, source = update
    (root / source).write_bytes(b'other user change')
    with pytest.raises(AssertionError, match='changed DGX source'):
        apply(archive, digest, root)
    assert (root / source).read_bytes() == b'other user change'
    assert not (root / 'outputs/s01_pre_hardening_backup.zip').exists()


def test_transfer_hash_mismatch_fails_before_any_write(update):
    root, archive, _, source = update
    with pytest.raises(AssertionError, match='archive hash mismatch'):
        apply(archive, '0' * 64, root)
    assert (root / source).read_bytes() == b'old source'
    assert not (root / 'outputs/s01_pre_hardening_backup.zip').exists()
