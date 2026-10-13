"""Frozen availability/weight interface audit; not real signal degradation."""
from __future__ import annotations
import json
import platform
import time
from pathlib import Path
from importlib.metadata import version

import numpy as np
from threadpoolctl import threadpool_limits
from neurofusion_qa.gating import continuous_utility, label_free_quality_weight, soft_fusion
from neurofusion_qa.provenance import canonical_json, canonical_json_sha256, sha256_file
import s01_comparator_benchmark as benchmark

ROOT=Path(__file__).resolve().parents[1]
PROTOCOL_SHA256="d060ffdcacf56d17393dec0216903cea949bc01ec8ddd791993baf2bfc1eb3c4"
PROTOCOL_COMMIT="20c6d44"


def load_protocol():
    protocol=json.loads((ROOT / 'config/s01_robustness_protocol.json').read_text(encoding='utf-8'))
    if canonical_json_sha256(protocol)!=PROTOCOL_SHA256:
        raise ValueError('Frozen robustness protocol hash mismatch')
    return protocol


def available_weight(weight, eeg_available, fmri_available):
    weight=np.asarray(weight,dtype=float)
    eeg=np.asarray(eeg_available); fmri=np.asarray(fmri_available)
    if eeg.shape!=weight.shape or fmri.shape!=weight.shape:
        raise ValueError('availability and weight shapes must match')
    if not np.all(np.isin(eeg,[0,1])) or not np.all(np.isin(fmri,[0,1])):
        raise ValueError('availability must be binary')
    if not np.isfinite(weight).all() or np.any((weight<0)|(weight>1)):
        raise ValueError('weight must be finite in [0,1]')
    return label_free_quality_weight((1-weight)*eeg, weight*fmri)


def check_contracts():
    p=np.array([.2,.9,.4]); q=np.array([.8,.3,.6]); w=np.array([.3,.5,.8])
    ones=np.ones(3); zeros=np.zeros(3)
    np.testing.assert_array_equal(soft_fusion(p,q,available_weight(w,ones,zeros)),p)
    np.testing.assert_array_equal(soft_fusion(p,q,available_weight(w,zeros,ones)),q)
    failures=[]
    for name,operation in [
        ('both_unavailable',lambda:available_weight(w,zeros,zeros)),
        ('invalid_availability',lambda:available_weight(w,[.5,1,1],ones)),
        ('nonfinite_weight',lambda:available_weight([np.nan,.5,.8],ones,ones)),
        ('unavailable_positive_mass',lambda:available_weight([0,0,0],zeros,ones))]:
        try: operation()
        except ValueError as error: failures.append({'case':name,'exception':'ValueError','diagnostic':str(error)})
        else: raise AssertionError(name)
    return {'only_eeg_endpoint':True,'only_fmri_endpoint':True,'failure_cases':failures,
        'zero_mass_limitation':'Availability alone cannot rescue a modality with exactly zero reliability mass; explicit normalization rejects rather than inventing a weight.'}


def uncertainty(y, probability, indices):
    if probability.ndim==2:
        probability=probability.mean(axis=0)
    errors=(probability-y)**2
    samples=errors[indices].mean(axis=1)
    low,high=np.quantile(samples,[.025,.975])
    return {'brier_score':float(errors.mean()),'ci_low':float(low),'ci_high':float(high)}


def sweeps(y, eeg, fmri, weight, strata, protocol):
    base=benchmark.load_protocol()
    ids=benchmark.stratified_indices(y,strata,base['uncertainty']['resamples'],base['uncertainty']['seed'])
    rng=np.random.default_rng(protocol['missingness_seed'])
    variates=rng.uniform(size=y.size)
    rows=[]
    for unavailable in protocol['availability']:
        for fraction in protocol['missing_fractions']:
            availability=(variates>=fraction).astype(int)
            mask=np.broadcast_to(availability,weight.shape)
            ea=mask if unavailable=='eeg_missing' else np.ones_like(weight,dtype=int)
            fa=mask if unavailable=='fmri_missing' else np.ones_like(weight,dtype=int)
            for name,w in [('quality',weight),('equal',np.full_like(weight,.5))]:
                actual=available_weight(w,ea,fa)
                p=soft_fusion(eeg,fmri,actual)
                assert np.isfinite(p).all() and np.all((p>=0)&(p<=1))
                rows.append({'experiment':unavailable,'level':fraction,'method':name,
                    'missing_records':int((availability==0).sum()),'records':int(y.size),**uncertainty(y,p,ids)})
    ablations={'informative':weight,'permuted_record_weights':weight[...,rng.permutation(y.size)],
        'reversed_weights':1-weight,'equal_weights':np.full_like(weight,.5)}
    for name,w in ablations.items():
        rows.append({'experiment':'quality_ablation','level':name,'method':'fusion','records':int(y.size),**uncertainty(y,soft_fusion(eeg,fmri,w),ids)})
    for level in protocol['probability_shrinkage_levels']:
        perturbed=(1-level)*fmri+level*.5
        for name,w in [('quality',label_free_quality_weight(1-weight,weight*(1-level))),('equal',np.full_like(weight,.5))]:
            rows.append({'experiment':'probability_shrinkage','level':level,'method':name,'records':int(y.size),**uncertainty(y,soft_fusion(eeg,perturbed,w),ids)})
    return rows


def timings(protocol):
    rng=np.random.default_rng(protocol['timing_seed']); rows=[]
    with threadpool_limits(limits=1):
        for count in protocol['timing_record_counts']:
            eeg,fmri,weight=rng.uniform(size=(3,count))
            y=rng.integers(0,2,count)
            quality_eeg,quality_fmri=rng.uniform(.01,1,size=(2,count))
            operations={'soft_fusion':lambda:soft_fusion(eeg,fmri,weight),
                'quality_normalization':lambda:label_free_quality_weight(quality_eeg,quality_fmri),
                'held_out_utility':lambda:continuous_utility(y,eeg,fmri)}
            for name,operation in operations.items():
                for _ in range(protocol['timing_warmups']): operation()
                samples=[]
                for _ in range(protocol['timing_repetitions']):
                    start=time.perf_counter_ns(); operation(); samples.append((time.perf_counter_ns()-start)/1e6)
                q25,median,q75=np.quantile(samples,[.25,.5,.75])
                rows.append({'operation':name,'records':count,'repetitions':len(samples),'median_ms':float(median),
                    'q25_ms':float(q25),'q75_ms':float(q75),'min_ms':min(samples),'max_ms':max(samples)})
    return rows


def repeat_predictions(protocol,seed,condition):
    """Same unimodal nested fitting as frozen 03; retain repeats for perturbation.

    No held-out label is used in model or quality fitting. Thresholds and the
    constant comparator are unnecessary here: this audit uses only Brier error.
    """
    from sklearn.model_selection import StratifiedKFold
    from sklearn.metrics import brier_score_loss
    labels,values,quality=benchmark.fixture(protocol,seed,condition)
    shape=(protocol['splits']['outer_repeats'],labels.size)
    p={name:np.full(shape,np.nan) for name in ('eeg','fmri')}
    weights=np.full(shape,np.nan)
    model_seed=protocol['splits']['model_seed']
    for repeat in range(shape[0]):
        outer=StratifiedKFold(protocol['splits']['outer_folds'],shuffle=True,random_state=model_seed+repeat)
        for train,test in outer.split(values['eeg'],labels):
            inner=list(StratifiedKFold(protocol['splits']['inner_folds'],shuffle=True,random_state=model_seed+repeat).split(values['eeg'][train],labels[train]))
            for name in p:
                losses=[]
                for c in protocol['c_grid']:
                    candidate=np.full(train.size,np.nan)
                    for fit,valid in inner:
                        model=benchmark.make_classifier(c=c,seed=model_seed)
                        model.fit(values[name][train[fit]],labels[train[fit]])
                        candidate[valid]=model.predict_proba(values[name][train[valid]])[:,1]
                    losses.append(brier_score_loss(labels[train],candidate))
                selected=protocol['c_grid'][int(np.argmin(losses))]
                model=benchmark.make_classifier(c=selected,seed=model_seed)
                model.fit(values[name][train],labels[train])
                p[name][repeat,test]=model.predict_proba(values[name][test])[:,1]
            weights[repeat,test]=benchmark.quality_weights(quality,train,test)
    assert all(np.isfinite(array).all() for array in [*p.values(),weights])
    return labels,p,weights


def run_audit(protocol=None):
    protocol=load_protocol() if protocol is None else protocol
    original=benchmark.load_protocol()
    y=[]; eeg=[]; fmri=[]; weights=[]; strata=[]
    with threadpool_limits(limits=1):
        for seed in protocol['fixture_seeds']:
            labels,p,w=repeat_predictions(original,seed,protocol['base_quality'])
            y.append(labels); eeg.append(p['eeg']); fmri.append(p['fmri']); weights.append(w); strata.extend([seed]*len(labels))
    y=np.concatenate(y)
    eeg,fmri,weights=[np.concatenate(arrays,axis=1) for arrays in (eeg,fmri,weights)]
    rows=sweeps(y,eeg,fmri,weights,np.array(strata),protocol)
    replay=sweeps(y,eeg,fmri,weights,np.array(strata),protocol)
    assert canonical_json_sha256(rows)==canonical_json_sha256(replay)
    frozen=json.loads((ROOT/'notebooks/artifacts/03_comparator_results.json').read_text(encoding='utf-8'))
    actual=float(np.mean((soft_fusion(eeg,fmri,weights).mean(axis=0)-y)**2))
    expected=frozen['conditions']['informative']['profiles']['quality']['brier_score']['value']
    assert np.isclose(actual,expected,atol=1e-12,rtol=0), 'Base predictions differ from frozen comparator evidence'
    sources=[Path(__file__),ROOT/'scripts/s01_comparator_benchmark.py',*sorted((ROOT/'src/neurofusion_qa').glob('*.py'))]
    return {'protocol_sha256':PROTOCOL_SHA256,'protocol_commit':PROTOCOL_COMMIT,'scope':protocol['scope'],
        'contracts':check_contracts(),'sweeps':rows,'deterministic_sweep_replay':True,'base_matches_03':True,
        'timings':timings(protocol),'memory_measured':False,'metadata':{'python':platform.python_version(),
            'platform':platform.system(),'machine':platform.machine(),'cpu':platform.processor() or 'not reported',
            'packages':{name:version(name) for name in ('numpy','scipy','scikit-learn','threadpoolctl')},
            'gpu_used':False,'source_sha256':{p.relative_to(ROOT).as_posix():sha256_file(p) for p in sources}}}


def write_audit(result):
    path=ROOT/'notebooks/artifacts/04_robustness_results.json'
    path.write_text(canonical_json(result)+'\n',encoding='utf-8')
    print('Saved 04 audit:',len(result['sweeps']),'sweep rows;',len(result['timings']),'timing rows',flush=True)
    return path


if __name__=='__main__': write_audit(run_audit())
