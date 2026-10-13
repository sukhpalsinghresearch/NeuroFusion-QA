"""Wheel certification must not accidentally test an editable checkout."""
import importlib.util
from pathlib import Path
from zipfile import ZipFile

import pytest

spec = importlib.util.spec_from_file_location(
    'check_wheel_install', Path(__file__).resolve().parents[1] / 'scripts/check_wheel_install.py')
wheel_check = importlib.util.module_from_spec(spec)
spec.loader.exec_module(wheel_check)


@pytest.fixture
def fixture_wheel(tmp_path):
    package = tmp_path / 'src/neurofusion_qa'
    package.mkdir(parents=True)
    (package / '__init__.py').write_bytes(b'"""fixture"""\n')
    (tmp_path / 'LICENSE').write_bytes(b'fixture license\n')
    path = tmp_path / 'fixture.whl'
    payload = {'neurofusion_qa/__init__.py': (package / '__init__.py').read_bytes()}
    for name in ('METADATA', 'WHEEL', 'RECORD'):
        payload['neurofusion_qa-0.1.0.dist-info/' + name] = b'fixture metadata'
    return tmp_path, path, payload


def save(path, payload):
    with ZipFile(path, 'w') as archive:
        for name, content in payload.items():
            archive.writestr(name, content)


def test_wheel_source_parity(fixture_wheel):
    root, path, payload = fixture_wheel
    for name in ('LICENSE', 'Licence.txt'):
        payload['neurofusion_qa-0.1.0.dist-info/licenses/' + name] = (root / 'LICENSE').read_bytes()
    save(path, payload)
    assert set(wheel_check.inspect_wheel(path, root)) == {'neurofusion_qa/__init__.py'}


@pytest.mark.parametrize('change', ['stale', 'missing', 'private_payload', 'metadata',
                                    'license', 'license_alias'])
def test_invalid_wheel_fails_closed(fixture_wheel, change):
    root, path, payload = fixture_wheel
    if change == 'stale':
        payload['neurofusion_qa/__init__.py'] = b'stale code'
    elif change == 'missing':
        del payload['neurofusion_qa/__init__.py']
    elif change == 'private_payload':
        payload['outputs/.fonts/private.ttf'] = b'private fixture'
    elif change in ('license', 'license_alias'):
        name = 'LICENSE' if change == 'license' else 'Licence.txt'
        payload['neurofusion_qa-0.1.0.dist-info/licenses/' + name] = b'changed license'
    else:
        del payload['neurofusion_qa-0.1.0.dist-info/RECORD']
    save(path, payload)
    with pytest.raises(ValueError):
        wheel_check.inspect_wheel(path, root)


def test_checkout_import_rejected(tmp_path):
    source = tmp_path / 'src/neurofusion_qa/__init__.py'
    with pytest.raises(ValueError, match='installed wheel'):
        wheel_check.require_installed_origin(source, source, tmp_path)


def test_wrong_distribution_import_rejected(tmp_path):
    with pytest.raises(ValueError, match='installed wheel'):
        wheel_check.require_installed_origin(tmp_path / 'wrong/__init__.py',
                                             tmp_path / 'site-packages/neurofusion_qa/__init__.py', tmp_path)


def test_installed_import_accepted(tmp_path):
    installed = tmp_path / 'env/site-packages/neurofusion_qa/__init__.py'
    wheel_check.require_installed_origin(installed, installed, tmp_path)
