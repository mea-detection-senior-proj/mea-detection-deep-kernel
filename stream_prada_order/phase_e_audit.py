"""Reproduce shortcut diagnostics from saved numeric metadata, without raw queries."""
import argparse
import gzip
import json
import math
from pathlib import Path
import time

import numpy as np
import phase_e_analysis as e


def verify_hashes(path):
    e.da.verify_hashes(path)


def read_gz(path): return json.loads(gzip.decompress(path.read_bytes()))


def audit(path):
    started=time.perf_counter(); verify_hashes(path)
    meta=json.loads((path/'metadata.json').read_text(encoding='utf-8')); cfg=meta['config']
    e.d.require(meta['status']=='completed_bounded_shortcut_analysis','Incomplete attempt')
    for name,h in meta['frozen_sources'].items(): e.d.require(e.fb.sha(e.ROOT/name)==h,'Frozen source drift')
    source=e.ROOT/cfg['phase_d_run']; verify_hashes(source)
    records=read_gz(source/'development_traces.json.gz'); features=read_gz(path/'query_metadata.json.gz'); growth=read_gz(path/'growth_paths.json.gz')
    e.d.require(len(records)==len(growth)==285,'Trace count mismatch')
    certificate=e.ROOT/'stream_prada_order/diagnostics/phase_b_plan/proposed_article_model_leeching_12_3_8.json.gz'
    cohorts=read_gz(certificate); e.fb.validate_allocation(cohorts)
    for cid,f in features.items():
        cid=int(cid); e.d.check_cohort(cid)
        for label in ['B','A']:
            e.d.require([r['query_sha256'] for r in f[label]]==cohorts[cid][label],'Query hash/order mismatch')
        e.d.require({r['article'] for label in ['B','A'] for r in f[label]}=={f['article']},'Within-cohort source mismatch')
    for r in records:
        e.d.check_cohort(r['cohort'])
        e.d.require(e.reconstruct_growth(r['distances'])==growth[f'{r["cohort"]}|{r["key"]}'],'Growing state mismatch')
    fit=e.fit_models(records,features,cfg)
    e.d.require(fit==json.loads((path/'fit_parameters.json').read_text(encoding='utf-8')),'Fit mismatch')
    curves={(r['cohort'],r['key']):e.curves(r,features,fit,cfg) for r in records}
    thresholds=json.loads((path/'thresholds.json').read_text(encoding='utf-8'))
    e.d.require(not thresholds['development_scored_at_freeze'],'Development used before threshold freeze')
    for name,hs in thresholds['thresholds'].items():
        scores=[e.d.maximum(curves[(r['cohort'],r['key'])][name]) for r in records if r['cohort'] in cfg['calibration_cohorts']]
        e.d.require(scores==thresholds['stream_maxima'][name],'Calibration maxima mismatch')
        for h in hs:
            rank=math.ceil(9*(1-h['alpha'])); expected=sorted(scores)[rank-1] if rank<=8 else None
            e.d.require(h['rank']==rank and h['threshold']==expected and h['finite']==(rank<=8),'Rank/infinity mismatch')
    rows=e.ca.read_rows(path/'per_stream.csv.gz'); typed=[]
    ids={(int(r['cohort']),r['key'],r['candidate'],float(r['alpha'])) for r in rows}
    expected={(r['cohort'],r['key'],name,a) for r in records if r['cohort'] in [12,13,14] for name in thresholds['thresholds'] for a in cfg['alphas']}
    e.d.require(ids==expected and len(rows)==len(ids)==13923,'Incomplete/colliding result ledger')
    for r in rows:
        cid=int(r['cohort']); alpha=float(r['alpha']); name=r['candidate']; mixed=e.ca.bool_value(r['has_attack'])
        curve=curves[(cid,r['key'])][name]; h=next(h for h in thresholds['thresholds'][name] if h['alpha']==alpha)
        metrics=e.metric_row(*curve,h,mixed,name.startswith('surrogate_'))
        for key,value in metrics.items(): e.d.require(r[key]==('' if value is None else str(value)),f'Crossing/delay mismatch: {key}')
        e.d.require(abs(float(r['max_score'])-e.d.maximum(curve))<1e-12,'Score mismatch')
        typed.append({**r,**metrics,'cohort':cid,'alpha':alpha,'has_attack':mixed,'attack_count':int(r['attack_count']),
                      'permutation':int(r['permutation']),'max_score':float(r['max_score'])})
    reproduced=e.extend_summary(e.d.summarize(typed,list(thresholds['thresholds']),cfg['alphas']),typed)
    e.d.require(reproduced==read_gz(path/'summary.json.gz'),'Summary/rate/leave-out/order mismatch')
    assoc=e.associations(records,features,growth,fit,cfg)
    e.d.require(assoc==json.loads((path/'associations.json').read_text(encoding='utf-8')),'Association/common-support mismatch')
    for cell in reproduced['cells']:
        e.d.require(cell['detections']+cell['right_censored']==cell['eligible'],'Censor accounting mismatch')
        e.d.require(cell['eligible']+cell['pre_attack_alarms']==cell['schedules'],'Prefix accounting mismatch')
    e.d.require(meta['prior_tracked_files_unchanged'] and meta['frozen_sources_unchanged'] and meta['main_unchanged'],'Preservation failed')
    return {'status':'passed','traces_reproduced':285,'query_metadata_rows':4224,'calibration_scores_reproduced':136,
            'validation_rows_reproduced':13923,'candidates':17,'operating_levels':3,'outer_development_cohorts':3,
            'growth_paths_checked':285,'phase_d_parity_rows':json.loads((path/'phase_d_parity.json').read_text())['rows_checked'],
            'association_and_common_support_reproduced':True,'encoder_runs':0,'victim_calls':0,'upstream_detector_reruns':0,
            'raw_queries_required_for_audit':False,'phase_c_evaluation_opened':False,'audit_seconds':time.perf_counter()-started,
            'source_sha256':e.fb.sha(__file__),'input_artifact_manifest_sha256':e.fb.sha(path/'artifact_hashes.json')}


def tables(path,out):
    s=read_gz(path/'summary.json.gz'); lines=['# Phase E diagnostic tables','',
        'Development only: 3 outer source cohorts; 10 conditional schedules each. Counts have denominator 30.',
        'Surrogate rows are offline score-path crossings, not measured attack TPR or real detection delays.',
        'Endpoint controls decide at Q256 only; alpha .05 has infinite thresholds for every candidate.','']
    for a in [.2,.4]:
        lines += [f'## Nominal alpha {a}', '', '| Candidate | Benign FP/3 | Attack26 R/C/I | Attack64 R/C/I | Attack128 R/C/I |',
                  '| --- | --- | --- | --- | --- |']
        for ctrl in [c for c in s['controls'] if c['alpha']==a]:
            name=ctrl['candidate']; cs=[c for c in s['cells'] if c['candidate']==name and c['alpha']==a]
            groups=[' / '.join(str(c['detections']) for c in cs if c['attack_count']==count) for count in [26,64,128]]
            lines.append(f'| {name} | {ctrl["false_alarms"]}/3 | '+' | '.join(groups)+' |')
        lines += ['', '| Candidate | Attack128 median detected delay R/C/I | Changed detections RC/RI/CI /30 |', '| --- | --- | --- |']
        for ctrl in [c for c in s['controls'] if c['alpha']==a and not c['candidate'].startswith('surrogate_')]:
            name=ctrl['candidate']; cs=[c for c in s['cells'] if c['candidate']==name and c['alpha']==a and c['attack_count']==128]
            delays=' / '.join(str(c['median_detected_delay']) if c['median_detected_delay'] is not None else 'null' for c in cs)
            pairs=[c for c in s['order_sensitivity'] if c['candidate']==name and c['alpha']==a and c['attack_count']==128 and c['metric']=='detected']
            lines.append(f'| {name} | {delays} | '+' / '.join(str(c['changed']) for c in pairs)+' |')
        lines.append('')
    (out/'PHASE_E_TABLES.md').write_text('\n'.join(lines).rstrip()+'\n',encoding='utf-8',newline='\n')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('results',type=Path); parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args(); e.d.require(not args.output.exists(),'Refusing to overwrite audit')
    result=audit(args.results); args.output.mkdir(parents=True); e.d.write(args.output/'verification.json',result)
    tables(args.results,args.output)
    e.d.write(args.output/'artifact_hashes.json',{p.name:e.fb.sha(p) for p in args.output.iterdir() if p.is_file()})
    print(json.dumps(result,indent=2))
