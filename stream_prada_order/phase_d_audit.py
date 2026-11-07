"""Reproduce Phase D statistics from published numeric inputs, without BGE."""
import argparse
import gzip
import hashlib
import json
import math
from pathlib import Path
import time

import numpy as np

import phase_d_pilot as d
import phase_c_audit as ca


def verify_hashes(path):
    for name,expected in json.loads((path/'artifact_hashes.json').read_text()).items():
        d.require(d.original.sha(path/name)==expected,f'Artifact hash mismatch: {name}')


def audit(path):
    started=time.perf_counter(); verify_hashes(path)
    meta=json.loads((path/'metadata.json').read_text()); cfg=meta['config']
    d.require(meta['status']=='completed_bounded_development_pilot','Attempt did not complete')
    for name,expected in meta['frozen_sources'].items():
        d.require(d.original.sha(d.ROOT/name)==expected,'Frozen source changed')
    records=json.loads(gzip.decompress((path/'development_traces.json.gz').read_bytes()))
    d.require(len(records)==285 and len({(r['cohort'],r['key']) for r in records})==285,'Input ledger mismatch')
    for r in records: d.check_cohort(r['cohort'])
    fit=d.fit_distance([r['distances'] for r in records if r['cohort'] in cfg['fit_cohorts']],cfg['sigma_floor'])
    saved_fit=json.loads((path/'distance_fit.json').read_text())
    d.require(fit['mu']==saved_fit['mu'] and fit['sigma']==saved_fit['sigma'],'Fit reproduction mismatch')
    all_curves={(r['cohort'],r['key']):d.curves(r,fit,cfg) for r in records}
    thresholds=json.loads((path/'thresholds.json').read_text())
    d.require(not thresholds['validation_scored_at_freeze'],'Thresholds opened validation')
    for name,hs in thresholds['thresholds'].items():
        values=[d.maximum(all_curves[(r['cohort'],r['key'])][name]) for r in records if r['cohort'] in cfg['calibration_cohorts']]
        d.require(values==thresholds['stream_maxima'][name],'Calibration statistic mismatch')
        for h in hs:
            rank=math.ceil(9*(1-h['alpha'])); expected=sorted(values)[rank-1] if rank<=8 else None
            d.require(h['rank']==rank and h['threshold']==expected and h['finite']==(rank<=8),'Rank calibration mismatch')
    rows=ca.read_rows(path/'per_stream.csv.gz')
    identities={(int(r['cohort']),r['key'],r['candidate'],float(r['alpha'])) for r in rows}
    expected_ids={(r['cohort'],r['key'],name,a) for r in records if r['cohort'] in [12,13,14]
                  for name in thresholds['thresholds'] for a in cfg['alphas']}
    d.require(identities==expected_ids and len(rows)==len(identities)==8190,'Candidate ledger mismatch')
    typed=[]
    for r in rows:
        cid=int(r['cohort']); alpha=float(r['alpha']); name=r['candidate']
        steps,values=all_curves[(cid,r['key'])][name]
        h=next(h for h in thresholds['thresholds'][name] if h['alpha']==alpha)
        first=next((s for s,v in zip(steps,values) if h['finite'] and v>h['threshold']),None)
        mixed=ca.bool_value(r['has_attack']); early=first is not None and first<=110
        expected={'any_alert':first is not None,'first_alert':first,'prefix_alarm':early,
                  'eligible':not early if mixed else None,'detected':not early and first is not None if mixed else None,
                  'delay':first-111 if mixed and not early and first is not None else None,
                  'right_censored':not early and first is None if mixed else None}
        for field,value in expected.items():
            d.require(r[field]==('' if value is None else str(value)),f'First crossing/metric mismatch: {field}')
        d.require(abs(float(r['max_score'])-max(values))<1e-12,'Maximum score mismatch')
        typed.append({**r,**expected,'cohort':cid,'alpha':alpha,'has_attack':mixed,'attack_count':int(r['attack_count']),
                      'permutation':int(r['permutation']),'max_score':float(r['max_score'])})
    saved=json.loads((path/'summary.json').read_text())
    reproduced=d.summarize(typed,list(thresholds['thresholds']),cfg['alphas'])
    d.require(saved==reproduced,'Summary/paired comparison mismatch')
    for c in saved['cells']:
        d.require(c['detections']+c['right_censored']==c['eligible'],'Risk accounting mismatch')
        d.require(c['eligible']+c['pre_attack_alarms']==c['schedules'],'Prefix accounting mismatch')
    d.require(all(not h['finite'] for hs in thresholds['thresholds'].values() for h in hs if h['alpha']==.05),'Five-percent point improperly extrapolated')
    d.require(meta['encoder_runs']==meta['upstream_detector_reruns']==0 and not meta['phase_c_evaluation_used'],'Forbidden execution')
    return {'status':'passed','published_numeric_inputs':285,'reproduced_calibration_scores':80,
            'reproduced_validation_rows':8190,'candidates':10,'operating_levels':3,
            'fit_calibration_validation_outer_n':[4,8,3],'five_percent_finite_thresholds':0,
            'encoder_runs':0,'original_upstream_detector_reruns':0,'phase_c_evaluation_opened':False,
            'audit_seconds':time.perf_counter()-started,'source_sha256':d.original.sha(__file__),
            'input_artifact_manifest_sha256':d.original.sha(path/'artifact_hashes.json')}


def tables_and_cohort_plot(path,out):
    summary=json.loads((path/'summary.json').read_text()); lines=['# Phase D detailed diagnostic tables','',
        'Development only: 3 reused cohorts, 10 schedules per cohort. Each TPR cell has 30 schedules.',
        'Columns show post-onset first detections/all schedules; all prefix alarms were zero in this run.',
        'Nominal alpha is not an established matched population FPR. Alpha 0.05 has infinite thresholds.', '']
    for alpha in [.2,.4]:
        lines += [f'## Nominal alpha {alpha}', '', '| Candidate | FP / 3 | TPR26 R/C/I | TPR64 R/C/I | TPR128 R/C/I |',
                  '| --- | --- | --- | --- | --- |']
        for control in [c for c in summary['controls'] if c['alpha']==alpha]:
            name=control['candidate']; cells=[c for c in summary['cells'] if c['candidate']==name and c['alpha']==alpha]
            groups=[' / '.join(f'{c["detections"]}/30' for c in cells if c['attack_count']==count) for count in [26,64,128]]
            lines.append(f'| {name} | {control["false_alarms"]}/3 | '+' | '.join(groups)+' |')
        lines += ['', '| Candidate | 50% median detected delay R/C/I | 50% changed detection pairs RC/RI/CI |', '| --- | --- | --- |']
        for control in [c for c in summary['controls'] if c['alpha']==alpha]:
            name=control['candidate']; cells=[c for c in summary['cells'] if c['candidate']==name and c['alpha']==alpha and c['attack_count']==128]
            ds=' / '.join('null' if c['median_detected_delay'] is None else str(c['median_detected_delay']) for c in cells)
            pairs=[c for c in summary['order_sensitivity'] if c['candidate']==name and c['alpha']==alpha and c['attack_count']==128 and c['metric']=='detected']
            ps=' / '.join(f'{c["changed"]}/30' for c in pairs)
            lines.append(f'| {name} | {ds} | {ps} |')
        lines.append('')
    (out/'PHASE_D_TABLES.md').write_text('\n'.join(lines)+'\n',encoding='utf-8',newline='\n')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    names=[c['candidate'] for c in summary['controls'] if c['alpha']==.2]
    values=[]
    for name in names:
        cells=[c for c in summary['cells'] if c['candidate']==name and c['alpha']==.2 and c['attack_count']==64]
        values.append([p['tpr_all_schedules'] for c in cells for p in c['per_cohort']])
    fig,ax=plt.subplots(figsize=(12,6),layout='constrained')
    im=ax.imshow(values,vmin=0,vmax=1,cmap='Blues',aspect='auto')
    ax.set(yticks=range(10),yticklabels=names,xticks=range(9),
           xticklabels=[f'{o[0].upper()} C{cid}' for o in d.original.ORDERS for cid in [12,13,14]],
           title='25% attack, alpha=0.20: 10 conditional schedules per cohort; inspect FPR separately')
    for i,row in enumerate(values):
        for j,v in enumerate(row): ax.text(j,i,f'{v:.0%}',ha='center',va='center',color='white' if v>.6 else 'black')
    fig.colorbar(im,ax=ax,label='Post-onset detections / all schedules (prefix alarms excluded from TP)')
    fig.savefig(out/'phase_d_cohort_variability.png',dpi=150); plt.close(fig)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('results',type=Path); parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args(); d.require(not args.output.exists(),'Refusing to overwrite audit')
    report=audit(args.results); args.output.mkdir(parents=True)
    d.write(args.output/'verification.json',report); tables_and_cohort_plot(args.results,args.output)
    d.write(args.output/'artifact_hashes.json',{p.name:d.original.sha(p) for p in args.output.iterdir() if p.is_file()})
    print(json.dumps(report,indent=2))
