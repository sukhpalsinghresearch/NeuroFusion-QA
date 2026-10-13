"""Verify a non-editable wheel import and exact package/source parity.

Run with the wheel environment's Python using -I. This check does not claim a
fresh dependency resolution by itself; the caller must create that environment.
"""
from __future__ import annotations

import argparse
import hashlib
from importlib import metadata
import json
from pathlib import Path
import platform
from zipfile import ZipFile


ROOT = Path(__file__).resolve().parents[1]


def inspect_wheel(wheel: Path, root: Path = ROOT) -> dict[str, str]:
    """Reject stale package code or unexpected non-package wheel payloads."""
    sources = {p.relative_to(root / 'src').as_posix(): p
               for p in (root / 'src/neurofusion_qa').rglob('*.py')}
    if not sources:
        raise ValueError('No package source files found')
    with ZipFile(wheel) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)):
            raise ValueError('Duplicate wheel members')
        metadata_names = [n for n in names if n.endswith('.dist-info/METADATA')]
        if len(metadata_names) != 1 or not metadata_names[0].startswith('neurofusion_qa-'):
            raise ValueError('Expected exactly one NeuroFusion-QA distribution')
        prefix = metadata_names[0].removesuffix('METADATA')
        allowed_metadata = {prefix + n for n in (
            'METADATA', 'WHEEL', 'RECORD', 'top_level.txt', 'LICENSE', 'licenses/LICENSE',
            'licenses/Licence.txt', 'LICENSE.txt', 'licenses/LICENSE.txt')}
        if set(names) - set(sources) - allowed_metadata:
            raise ValueError('Unexpected wheel payload: only package code and distribution metadata are allowed')
        if not {prefix + n for n in ('METADATA', 'WHEEL', 'RECORD')} <= set(names):
            raise ValueError('Missing required wheel metadata')
        if not set(sources) <= set(names):
            raise ValueError('Wheel is missing public package code')
        for name in ('LICENSE', 'licenses/LICENSE', 'licenses/Licence.txt', 'LICENSE.txt', 'licenses/LICENSE.txt'):
            if prefix + name in names and archive.read(prefix + name) != (root / 'LICENSE').read_bytes():
                raise ValueError(f'Wheel license differs from source: {name}')
        hashes = {}
        for name, path in sources.items():
            content = archive.read(name)
            if content != path.read_bytes():
                raise ValueError(f'Stale wheel source: {name}')
            hashes[name] = hashlib.sha256(content).hexdigest()
    return hashes


def require_installed_origin(module_path: Path, installed_path: Path, root: Path = ROOT) -> None:
    """Fail if import resolution reached the checkout or a different install."""
    actual = module_path.resolve()
    if actual.is_relative_to((root / 'src').resolve()) or actual != installed_path.resolve():
        raise ValueError('Package must import from the installed wheel, not the source checkout')


def verify_install(wheel: Path, root: Path = ROOT) -> dict:
    import neurofusion_qa

    hashes = inspect_wheel(wheel, root)
    distribution = metadata.distribution('neurofusion-qa')
    require_installed_origin(Path(neurofusion_qa.__file__),
                             Path(distribution.locate_file('neurofusion_qa/__init__.py')), root)
    direct = distribution.read_text('direct_url.json')
    if direct and json.loads(direct).get('dir_info', {}).get('editable'):
        raise ValueError('Editable installation cannot certify a built wheel')
    for name, expected in hashes.items():
        installed = Path(distribution.locate_file(name))
        if hashlib.sha256(installed.read_bytes()).hexdigest() != expected:
            raise ValueError(f'Installed package differs from the wheel: {name}')
    return {
        'scope': 'installed_wheel_code_parity_not_full_platform_certification',
        'passed': True, 'import_origin': 'installed_distribution_not_source_checkout',
        'editable': False, 'wheel_sha256': hashlib.sha256(wheel.read_bytes()).hexdigest(),
        'package_file_sha256': hashes, 'python': platform.python_version(),
        'platform': platform.system(),
        'packages': {name: metadata.version(name) for name in
                     ('neurofusion-qa', 'numpy', 'scipy', 'scikit-learn')},
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--wheel', type=Path, required=True)
    parser.add_argument('--report', type=Path, default=ROOT / 'outputs/wheel_install_verification.json')
    args = parser.parse_args()
    report = verify_install(args.wheel.resolve())
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(f"Wheel verified: {len(report['package_file_sha256'])} package files; "
          f"non-editable installed import; Python {report['python']} / {report['platform']}")
