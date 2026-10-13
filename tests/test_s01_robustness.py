import importlib.util
from pathlib import Path
import sys
import numpy as np
import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
spec=importlib.util.spec_from_file_location('s01_audit',ROOT/'scripts/s01_robustness_audit.py')
audit=importlib.util.module_from_spec(spec); spec.loader.exec_module(audit)


def test_frozen_robustness_protocol():
    assert audit.load_protocol()['protocol_id']=='s01-interface-robustness-v1'


def test_available_endpoints_and_failure_contracts():
    report=audit.check_contracts()
    assert report['only_eeg_endpoint'] and report['only_fmri_endpoint']
    assert len(report['failure_cases'])==4


@pytest.mark.parametrize('weight,eeg,fmri', [([.5],[0],[0]),([.5],[.5],[1]),([np.nan],[1],[1]),([.5],[1,1],[1])])
def test_invalid_availability_rejected(weight,eeg,fmri):
    with pytest.raises(ValueError): audit.available_weight(weight,eeg,fmri)


def test_sweep_replay_counts_and_all_missing_recovery():
    y=np.tile([0,1],12); eeg=np.linspace(.1,.8,24); fmri=np.linspace(.2,.9,24)
    weight=np.linspace(.3,.7,24); strata=np.repeat([1,2,3],8)
    protocol=audit.load_protocol()
    rows=audit.sweeps(y,eeg,fmri,weight,strata,protocol)
    assert len(rows)==38
    assert rows==audit.sweeps(y,eeg,fmri,weight,strata,protocol)
    for missing,recovered in [('eeg_missing',fmri),('fmri_missing',eeg)]:
        endpoints=[r for r in rows if r['experiment']==missing and r['level']==1]
        assert len(endpoints)==2
        for row in endpoints:
            assert row['missing_records']==24
            np.testing.assert_allclose(row['brier_score'],np.mean((recovered-y)**2))


def test_repeat_adapter_agrees_with_frozen_predictions():
    protocol=audit.benchmark.load_protocol()
    protocol['c_grid']=[.1]
    y,p,w=audit.repeat_predictions(protocol,20261011,'informative')
    expected_y,expected,_,expected_w,_=audit.benchmark.nested_predictions(protocol,20261011,'informative')
    np.testing.assert_array_equal(y,expected_y)
    for name in ('eeg','fmri'):
        np.testing.assert_allclose(p[name].mean(axis=0),expected[name],atol=1e-12,rtol=0)
    np.testing.assert_allclose(w.mean(axis=0),expected_w,atol=1e-12,rtol=0)
    np.testing.assert_allclose(audit.soft_fusion(p['eeg'],p['fmri'],w).mean(axis=0),expected['quality'],atol=1e-12,rtol=0)
