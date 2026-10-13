"""Reconcile S01 calculations and release readiness without changing frozen experiments.

Run after notebook 04 or as a standalone audit. Open requirements are evidence,
not exceptions to hide. No experimental parameter or public implementation is changed.
"""
from __future__ import annotations

import csv
import json
import platform
import warnings
from importlib.metadata import version
from pathlib import Path

import numpy as np
from scipy.integrate import trapezoid

from neurofusion_qa.evaluation import paired_subject_bootstrap
from neurofusion_qa.features import fisher_connectivity
from neurofusion_qa.gating import equal_fusion, label_free_quality_weight
from neurofusion_qa.integrity import validate_compact_features
from neurofusion_qa.provenance import canonical_json, canonical_json_sha256, sha256_file
from neurofusion_qa.quality import RobustQualityScaler

ROOT = Path(__file__).resolve().parents[1]


def calculation_crosscheck(results):
    """Independent aggregate identities, not a refit or a second bootstrap."""
    checks = 0
    for evidence in results['conditions'].values():
        n = evidence['records']
        for method, profile in evidence['profiles'].items():
            tn, fp, fn, tp = np.asarray(evidence['confusion'][method]).ravel()
            assert min(tn, fp, fn, tp) >= 0 and tn + fp + fn + tp == n
            assert tp + fn > 0 and tn + fp > 0
            divide = lambda a, b: a / b if b else 0.0
            sensitivity, specificity = tp / (tp + fn), tn / (tn + fp)
            expected = {
                'accuracy': (tp + tn) / n,
                'balanced_accuracy': (sensitivity + specificity) / 2,
                'precision': divide(tp, tp + fp), 'sensitivity': sensitivity,
                'specificity': specificity, 'f1': divide(2 * tp, 2 * tp + fp + fn),
                'mcc': divide(tp * tn - fp * fn,
                              np.sqrt(float((tp + fp) * (tp + fn) * (tn + fp) * (tn + fn)))),
            }
            calibration = evidence['calibration'][method]
            assert sum(row['count'] for row in calibration) == n
            expected['ece_10_uniform'] = sum(
                row['count'] / n * abs(row['mean_probability'] - row['positive_fraction'])
                for row in calibration if row['count'])
            curve = evidence['curves'][method]
            expected['roc_auc'] = trapezoid(curve['tpr'], curve['fpr'])
            expected['average_precision'] = -np.sum(
                np.diff(curve['recall']) * np.asarray(curve['precision'])[:-1])
            for metric, value in expected.items():
                np.testing.assert_allclose(profile[metric]['value'], value, atol=1e-12, rtol=0)
                checks += 1
            for metric, row in profile.items():
                assert np.isfinite(list(row.values())).all()
                assert row['ci_low'] <= row['ci_high']
                if metric != 'log_loss':
                    lower = -1 if metric == 'mcc' else 0
                    assert lower - 1e-12 <= row['value'] <= 1 + 1e-12
                    assert lower - 1e-12 <= row['ci_low'] <= row['ci_high'] <= 1 + 1e-12
                else:
                    assert row['ci_low'] >= 0 and row['value'] >= 0
                checks += 1
        for row in evidence['paired_differences']:
            point = (evidence['profiles'][row['candidate']][row['metric']]['value'] -
                     evidence['profiles'][row['reference']][row['metric']]['value'])
            np.testing.assert_allclose(row['difference'], point, atol=1e-12, rtol=0)
            assert row['ci_low'] <= row['ci_high']
            assert row['interval_spans_zero'] == (row['ci_low'] <= 0 <= row['ci_high'])
            checks += 1
    return {'passed': True, 'identities_checked': checks,
            'scope': 'aggregate consistency; metric oracle and bootstrap-pairing tests are separate',
            'uncertainty': 'conditional record bootstrap, not population or model-refitting uncertainty',
            'brier_log_loss': 'Brier uses original probabilities; log loss clips at 1e-6 as frozen in 03',
            'binary_metrics': 'training-selected thresholds and repeat majority votes, ties positive; not thresholding mean probabilities'}


def verify_core_artifacts():
    """Validate existing core record envelopes, boundaries and bound source files."""
    artifacts = ROOT / 'notebooks/artifacts'
    records = {}
    for name in ('00_preflight_report.json', '01_feature_contracts.json', '01_core_workflow.json'):
        record = json.loads((artifacts / name).read_text(encoding='utf-8'))
        digest = record.pop('canonical_content_sha256')
        assert canonical_json_sha256(record) == digest, f'core content hash mismatch: {name}'
        assert record['boundary']['e01_participant_level_access'] is False
        assert record['boundary']['e01_results_consumed'] is False
        records[name] = record
    core = records['01_core_workflow.json']
    assert sha256_file(ROOT / core['feature_evidence']['path']) == core['feature_evidence']['file_sha256']
    for name, digest in core['source_sha256'].items():
        path = (ROOT / name).resolve()
        assert path.is_relative_to(ROOT) and sha256_file(path) == digest, f'stale core source: {name}'
    assert len(core['qc']['threshold_cases']) == 20
    assert core['quality']['held_out_transform_preserves_fit']
    assert core['modelling']['same_seed_replay_matches']
    return 'three canonical envelopes/boundaries, core feature/source hashes and representative assertions verified'


def failure_matrix():
    """Execute representative cases; preserve observed contract gaps as open rows."""
    rows = []

    def probe(case, operation, accepts, expectation, category):
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter('always')
            try:
                value = operation()
            except (ValueError, RuntimeError, AssertionError, np.linalg.LinAlgError) as error:
                observed = type(error).__name__ + ': ' + str(error)
                passed = accepts(None, error)
            else:
                observed = 'returned ' + repr(value)
                passed = accepts(value, None)
        rows.append({'case': case, 'category': category, 'expected': expectation,
                     'observed': observed, 'status': 'pass' if passed else 'open_gap',
                     'warnings': ' | '.join(str(w.message) for w in caught)})

    rejected = lambda value, error: error is not None
    finite_or_rejected = lambda value, error: error is not None or np.isfinite(value).all()
    for case, operation in [
        ('nan_probability', lambda: equal_fusion([np.nan], [.4])),
        ('inf_probability', lambda: equal_fusion([np.inf], [.4])),
        ('negative_probability', lambda: equal_fusion([-.1], [.4])),
        ('above_one_probability', lambda: equal_fusion([1.1], [.4])),
        ('mismatched_probability_shape', lambda: equal_fusion([.2, .3], [.4])),
        ('negative_quality', lambda: label_free_quality_weight([-1], [1])),
        ('zero_total_quality', lambda: label_free_quality_weight([0], [0])),
        ('nonfinite_quality', lambda: label_free_quality_weight([np.inf], [1])),
        ('all_missing_training_quality', lambda: RobustQualityScaler.fit([[np.nan], [np.nan]])),
        ('degenerate_class_bootstrap', lambda: paired_subject_bootstrap(
            [0, 0], [.2, .3], [.1, .2], lambda y, p: np.mean((y - p) ** 2), n_resamples=10)),
    ]:
        probe(case, operation, rejected, 'reject invalid input', 'invalid_input')
    # Adopted release-hardening requirements; direct tests guard each fix.
    probe('empty_fusion', lambda: equal_fusion([], []), rejected,
          'explicitly reject empty evidence arrays', 'hardening')
    probe('extreme_quality_normalization', lambda: label_free_quality_weight([1e308], [1e308]),
          lambda v, e: e is not None or (np.isfinite(v).all() and np.allclose(v, [.5])),
          'equal finite positive masses give 0.5 or reject unsafe scaling', 'hardening')
    probe('infinite_training_quality', lambda: RobustQualityScaler.fit([[1], [np.inf], [2]]).transform([[2]]),
          finite_or_rejected, 'finite transformation or explicit rejection; no silent NaN', 'hardening')
    probe('constant_connectivity', lambda: fisher_connectivity(np.ones((3, 20))),
          finite_or_rejected, 'finite matrix or explicit rejection; no silent NaN', 'hardening')
    for name, values in [('empty_features', []), ('constant_features', [1, 1]), ('nan_features', [1, np.nan])]:
        probe(name, lambda values=values: validate_compact_features(values, (2,)).passed,
              lambda v, e: e is None and not v, 'integrity report rejects', 'integrity')
    probe('constant_quality_scaling', lambda: RobustQualityScaler.fit([[1], [1]]).transform([[1], [2]]),
          lambda v, e: e is None and np.isfinite(v).all() and np.max(np.abs(v)) <= 5,
          'finite clipped transform', 'quality')
    from s01_core_workflow import fusion_contracts, qc_contracts, quality_contracts
    from s01_robustness_audit import check_contracts
    from s01_provenance_tutorial import provenance_failures
    for row in fusion_contracts()['failures']:
        rows.append({'case': 'fusion_' + row['case'], 'category': 'fusion_contract',
                     'expected': 'ValueError with checked diagnostic', 'observed': row['message'],
                     'status': 'pass', 'warnings': ''})
    for row in check_contracts()['failure_cases']:
        rows.append({'case': 'availability_' + row['case'], 'category': 'availability_contract',
                     'expected': 'ValueError', 'observed': row['diagnostic'], 'status': 'pass', 'warnings': ''})
    # The existing tutorial scopes and cleans its temporary fixtures under outputs/.
    for row in provenance_failures():
        rows.append({'case': 'provenance_' + row['case'], 'category': 'provenance_contract',
                     'expected': 'ValueError with checked diagnostic', 'observed': row['message'],
                     'status': 'pass', 'warnings': ''})
    qc, quality = qc_contracts(), quality_contracts()
    assert len(qc['threshold_cases']) == 20 and quality['held_out_transform_preserves_fit']
    rows.append({'case': 'qc_boundaries_and_gate_independence', 'category': 'integration',
                 'expected': '20 boundaries and four independent gate combinations',
                 'observed': 'all assertions passed', 'status': 'pass', 'warnings': ''})
    rows.append({'case': 'training_only_quality_fit', 'category': 'integration',
                 'expected': 'held-out transform preserves fit; held-out extremes clipped',
                 'observed': 'all assertions passed', 'status': 'pass', 'warnings': ''})
    return rows


def write_csv(path, rows):
    fields = list(dict.fromkeys(key for row in rows for key in row))
    with path.open('w', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def checksums(root):
    """Snapshot aggregate artifacts and figure exports only; excludes itself/fonts."""
    names = sorted(p for folder in ('notebooks/artifacts', 'notebooks/figures')
                   for p in (root / folder).rglob('*') if p.is_file() and
                   p.name != 'SHA256SUMS.txt' and '.ipynb_checkpoints' not in p.parts)
    destination = root / 'notebooks/artifacts/SHA256SUMS.txt'
    destination.write_text(''.join(f'{sha256_file(p)}  {p.relative_to(root).as_posix()}\n'
                                   for p in names), encoding='utf-8')
    return len(names)


def verify_hardening_regression(archive):
    """Compare refreshed aggregate evidence with a preserved pre-fix snapshot."""
    import zipfile
    with zipfile.ZipFile(archive) as saved:
        comparisons = {}
        fingerprints = {}
        previous_sources = None
        current_sources = None
        for name, fields in [('03_comparator_results.json', ('conditions', 'folds', 'protocol_sha256')),
                             ('04_robustness_results.json', ('sweeps', 'contracts', 'protocol_sha256'))]:
            relative = 'notebooks/artifacts/' + name
            old_bytes = saved.read(relative)
            before = json.loads(old_bytes)
            after = json.loads((ROOT / relative).read_text(encoding='utf-8'))
            for field in fields:
                assert before[field] == after[field], f'nominal evidence changed: {name}/{field}'
                comparisons[name + '/' + field] = 'exact_match'
            import hashlib
            fingerprints[relative] = {'before_sha256': hashlib.sha256(old_bytes).hexdigest(),
                                      'after_sha256': sha256_file(ROOT / relative)}
            if name.startswith('03'):
                previous_sources = before['metadata']['source_sha256']
                current_sources = after['metadata']['source_sha256']
        assert set(previous_sources) == set(current_sources)
        changed = {name: {'before': previous_sources[name], 'after': current_sources[name]}
                   for name in previous_sources if previous_sources[name] != current_sources[name]}
        assert set(changed) == {'src/neurofusion_qa/gating.py', 'src/neurofusion_qa/quality.py',
                               'src/neurofusion_qa/features.py'}, 'unexpected numerical source change'
        assert all(sha256_file(ROOT / name) == digest for name, digest in current_sources.items())
    report = {'scope': 'pre_vs_post_hardening_synthetic_regression', 'comparisons': comparisons,
              'changed_sources': changed, 'artifact_sha256': fingerprints,
              'baseline_archive_sha256': sha256_file(archive), 'source_sha256': sha256_file(Path(__file__)),
              'timing_comparison': 'excluded: fresh runtime timings are not expected to be identical',
              'passed': True}
    (ROOT / 'notebooks/artifacts/04_hardening_regression.json').write_text(canonical_json(report) + '\n', encoding='utf-8')
    print('Hardening regression: comparator metrics/folds and robustness sweeps exactly unchanged; protocols unchanged', flush=True)
    return report


def run_release_audit():
    import subprocess
    import sys
    from verify_s01_evidence import verify_and_export
    print('Verifying frozen evidence and publication exports', flush=True)
    verify_and_export()  # Includes strict frozen-source and publication-export hashes.
    checks = {}
    checks['core_artifacts'] = verify_core_artifacts()
    for name, args in [('provenance', ['scripts/s01_provenance_tutorial.py', '--verify']),
                       ('release_boundary', ['scripts/validate_release.py'])]:
        print('Checking ' + name, flush=True)
        done = subprocess.run([sys.executable, *args], cwd=ROOT, check=True, text=True, capture_output=True)
        checks[name] = done.stdout.strip()
    artifacts = ROOT / 'notebooks/artifacts'
    results = json.loads((artifacts / '03_comparator_results.json').read_text(encoding='utf-8'))
    robust = json.loads((artifacts / '04_robustness_results.json').read_text(encoding='utf-8'))
    print('Cross-checking calculations and executing failure matrix', flush=True)
    calculations, failures = calculation_crosscheck(results), failure_matrix()
    write_csv(artifacts / '04_failure_matrix.csv', failures)
    write_csv(artifacts / '04_performance_results.csv', robust['timings'])
    write_csv(artifacts / '04_robustness_results.csv', robust['sweeps'])
    claims = []
    for claim, artifact, command, boundary in [
        ('Synthetic feature/QC/fusion contracts', '01_core_workflow.json', 'scripts/s01_core_workflow.py', 'software contracts, not biological validation'),
        ('Checked identity and manifest lineage', '02_execution_manifest.json', 'scripts/s01_provenance_tutorial.py', 'hash consistency, not cryptographic authenticity'),
        ('Five matched synthetic comparators, including unfavorable results', '03_comparator_results.json', 'scripts/s01_comparator_benchmark.py', '6/8 mathematical model inputs, not EEG-33/fMRI-1440 benchmark data'),
        ('Availability and weight perturbation sweeps', '04_robustness_results.json', 'scripts/s01_robustness_audit.py', 'prediction interface, not real signal noise'),
        ('Measured CPU kernel times', '04_performance_results.csv', 'scripts/s01_robustness_audit.py', 'one recorded environment; no GPU or peak-memory claim'),
        ('Publication export contract', '../figures/figure_index.json', 'scripts/s01_evidence_figures.py --section all', '1000-DPI/TNR source exports; final manuscript placement still needs visual review'),
    ]:
        path = (artifacts / artifact).resolve()
        claims.append({'claim': claim, 'status': 'supported_with_boundary',
                       'artifact': path.relative_to(ROOT).as_posix(), 'sha256': sha256_file(path),
                       'producing_command': 'python ' + command,
                       'software_version': version('neurofusion-qa'),
                       'revision': 'working tree; evidence bound by source hashes, not a tagged release',
                       'fixture_license': 'project-generated synthetic fixtures; repository BSD-3-Clause LICENSE; private fonts excluded',
                       'allowed_use': 'S01 software evidence only', 'boundary': boundary})
    for claim, boundary in [
        ('Clinical or cross-dataset generalization', 'no compatible licensed paired real datasets executed'),
        ('All-platform clean-install support', 'no verified public OS/Python/dependency CI matrix'),
        ('Native peak-memory results', 'not measured'),
        ('Complete direct-comparator literature review', 'current nine-paper map is targeted software evidence, not exhaustive/direct fusion reproduction'),
    ]:
        claims.append({'claim': claim, 'status': 'not_supported', 'boundary': boundary})
    write_csv(artifacts / '04_claim_evidence_ledger.csv', claims)
    gaps = [r['case'] for r in failures if r['status'] == 'open_gap']
    notebook_state = []
    for path in sorted((ROOT / 'notebooks').glob('0[0-4]_S01_*.ipynb')):
        notebook = json.loads(path.read_text(encoding='utf-8'))
        cells = [c for c in notebook['cells'] if c['cell_type'] == 'code']
        notebook_state.append({'path': path.relative_to(ROOT).as_posix(), 'code_cells': len(cells),
            'saved_executed_cells': sum(c['execution_count'] is not None for c in cells),
            'saved_error_outputs': sum(o['output_type'] == 'error' for c in cells for o in c['outputs']),
            'scope': 'saved-output inspection, not proof of a fresh current-source kernel execution'})
    open_gates = [
        'Run a fresh dependency-resolving install and built-wheel tests in the declared OS/Python/minimum/newest dependency matrix.',
        'Verify current-source ordered DGX kernel execution; archived earlier runs do not certify later source changes.',
        'Complete public API docs, contribution/governance/support, release archive DOI and author-approved declarations.',
        'Independent claim/boundary review and final manuscript-size visual review remain required.',
        'Sample-size/class-imbalance sensitivity is proposed, not part of either frozen protocol; preregister separately before running.',
    ]
    report = {'schema_version': '1.0', 'scope': 'synthetic_software_evidence_only',
        'submission_ready': False, 'checks': checks, 'calculations': calculations,
        'failure_matrix': {'cases': len(failures), 'passed': len(failures) - len(gaps), 'open_gaps': gaps},
        'notebooks': notebook_state, 'open_submission_gates': open_gates,
        'external_validation': 'conditional notebook 05 not started; synthetic seeds are not separate real datasets',
        'package_artifact_install': 'not executed by this audit; no clean-install certification',
        'environment': {'python': platform.python_version(), 'platform': platform.system(),
                        'packages': {n: version(n) for n in ('numpy', 'scipy', 'scikit-learn')}},
        'source_sha256': {p.relative_to(ROOT).as_posix(): sha256_file(p) for p in [
            Path(__file__), ROOT / 'scripts/verify_s01_evidence.py', ROOT / 'scripts/s01_core_workflow.py',
            ROOT / 'scripts/s01_provenance_tutorial.py', *sorted((ROOT / 'src/neurofusion_qa').glob('*.py'))]},
        'protocols': {name: results[name] for name in ('protocol_sha256', 'protocol_commit')},
        'robustness_protocol_sha256': robust['protocol_sha256']}
    (artifacts / '04_release_audit.json').write_text(canonical_json(report) + '\n', encoding='utf-8')
    total = checksums(ROOT)
    print(f"Release audit: {calculations['identities_checked']} calculation checks; "
          f"{len(failures) - len(gaps)}/{len(failures)} case requirements passed; {total} files checksummed; "
          'submission_ready=False')
    if gaps:
        print('Open hardening gaps: ' + ', '.join(gaps))
    return report


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline', type=Path, help='Preserved pre-hardening ZIP for independent nominal-result comparison')
    args = parser.parse_args()
    if args.baseline is not None:
        verify_hardening_regression(args.baseline)
    run_release_audit()
