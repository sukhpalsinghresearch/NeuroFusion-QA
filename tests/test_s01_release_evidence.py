"""Independent consistency checks and honest release-audit contracts."""
import copy
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import s01_release_evidence as audit


@pytest.fixture
def comparator():
    return json.loads((ROOT / 'notebooks/artifacts/03_comparator_results.json').read_text(encoding='utf-8'))


def test_aggregate_calculation_identities(comparator):
    result = audit.calculation_crosscheck(comparator)
    assert result['passed'] and result['identities_checked'] == 474
    assert 'conditional' in result['uncertainty']


@pytest.mark.parametrize('metric', ['accuracy', 'roc_auc', 'average_precision', 'ece_10_uniform'])
def test_inconsistent_aggregate_metric_fails_closed(comparator, metric):
    changed = copy.deepcopy(comparator)
    changed['conditions']['informative']['profiles']['quality'][metric]['value'] += .01
    with pytest.raises(AssertionError):
        audit.calculation_crosscheck(changed)


def test_inconsistent_paired_difference_fails_closed(comparator):
    comparator['conditions']['informative']['paired_differences'][0]['difference'] += .01
    with pytest.raises(AssertionError):
        audit.calculation_crosscheck(comparator)


def test_failure_matrix_confirms_all_four_hardening_fixes():
    rows = audit.failure_matrix()
    assert len({row['case'] for row in rows}) == len(rows)
    cases = {row['case']: row for row in rows}
    for name in ('nan_probability', 'inf_probability', 'degenerate_class_bootstrap',
                 'constant_features', 'provenance_tampered_manifest'):
        assert cases[name]['status'] == 'pass'
    for name in ('empty_fusion', 'extreme_quality_normalization',
                 'infinite_training_quality', 'constant_connectivity'):
        assert cases[name]['category'] == 'hardening'
        assert cases[name]['status'] == 'pass'
        assert not cases[name]['warnings']
        assert cases[name]['observed']


def test_checksums_exclude_private_outputs_and_themselves(tmp_path):
    artifacts = tmp_path / 'notebooks/artifacts'
    figures = tmp_path / 'notebooks/figures'
    fonts = tmp_path / 'outputs/.fonts'
    for folder in (artifacts, figures, fonts):
        folder.mkdir(parents=True)
    (artifacts / 'example.json').write_text('{}', encoding='utf-8')
    (figures / 'example.svg').write_text('<svg/>', encoding='utf-8')
    (fonts / 'private.ttf').write_bytes(b'private fixture, not a real font')
    assert audit.checksums(tmp_path) == 2
    first = (artifacts / 'SHA256SUMS.txt').read_text(encoding='utf-8')
    assert 'private.ttf' not in first and 'SHA256SUMS.txt' not in first
    assert audit.checksums(tmp_path) == 2
    assert (artifacts / 'SHA256SUMS.txt').read_text(encoding='utf-8') == first
