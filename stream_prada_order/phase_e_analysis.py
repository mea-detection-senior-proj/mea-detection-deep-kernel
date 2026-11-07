"""Bounded shortcut controls on saved development paths; no encoder/victim calls."""
from __future__ import annotations
import argparse
from collections import defaultdict
import gzip
import json
from pathlib import Path
import platform
import subprocess
import time

import numpy as np
import psutil
from scipy.stats import spearmanr

import phase_d_pilot as d
import phase_d_audit as da
import phase_b_feasibility as fb
import phase_c_audit as ca

ROOT=d.ROOT
HERE=d.HERE


def length_endpoint(words):
    return [256],[float(np.mean(np.log1p(words)))]


def distance_endpoint(distances):
    return [256],[-float(np.mean(np.asarray(distances)[100:]))]


def surrogate(z,name):
    z=np.asarray(z,dtype=float); result=z.copy()
    if name=='reverse': result[109:]=z[109:][::-1]
    else:
        d.require(name in ('shuffle17','shuffle29'),'Unknown fixed surrogate')
        result[109:]=np.random.default_rng(int(name.removeprefix('shuffle'))).permutation(z[109:])
    return result


def prefix_center(z): return np.asarray(z)-np.mean(np.asarray(z)[:100])


def reconstruct_growth(distances):
    dg=[0.]; threshold=0.; admitted=[True]; counts=[1]; thresholds=[0.]
    for value in distances:
        add=value>threshold; admitted.append(bool(add))
        if add:
            dg.append(value); threshold=max(threshold,float(np.mean(dg)-np.std(dg)))
        counts.append(len(dg)); thresholds.append(threshold)
    return {'admitted':admitted,'counts':counts,'thresholds':thresholds}


def fit_length(distances,u,floor):
    distances=np.asarray(distances); u=np.asarray(u)
    d.require(distances.shape==u.shape and distances.shape==(4,255),'Expected four fit cohorts')
    mu=distances.mean(axis=0); mean=u.mean(axis=0)
    centered=u-mean; denominator=float(np.sum(centered**2))
    d.require(denominator>0 and np.isfinite(distances).all() and np.isfinite(u).all(),'Degenerate length fit')
    beta=float(np.sum(centered*(distances-mu))/denominator)
    adjusted=distances-beta*centered
    return {'beta':beta,'u_mean':mean.tolist(),'mu':mu.tolist(),
            'sigma':np.maximum(adjusted.std(axis=0,ddof=1),floor).tolist(),
            'support':[float(u.min()),float(u.max())]}


def in_support(u,support):
    u=np.asarray(u); return (u>=support[0])&(u<=support[1])


def adjust_length(distances,u,fit):
    clipped=np.clip(u,*fit['support'])
    return np.asarray(distances)-fit['beta']*(clipped-np.asarray(fit['u_mean']))


def rho(x,y):
    x=np.asarray(x); y=np.asarray(y)
    if len(x)<3 or np.ptp(x)<1e-12 or np.ptp(y)<1e-12: return None
    result=float(spearmanr(x,y).statistic)
    return result if np.isfinite(result) else None


def overlap_counts(benign,attack,bins):
    b=np.histogram(benign,list(bins)+[np.inf])[0]; a=np.histogram(attack,list(bins)+[np.inf])[0]
    return {'benign_bins':b.tolist(),'attack_bins':a.tolist(),'matched_pair_capacity':int(np.minimum(b,a).sum())}


def leave_one_out(rows):
    return [float(np.mean([r['rate'] for r in rows if r['cohort']!=omitted])) for omitted in [12,13,14]]


def metric_row(steps,values,threshold,mixed,surrogate_path=False):
    row=d.crossing(steps,values,threshold,has_attack=mixed)
    row['surrogate_delay']=row['delay'] if surrogate_path else None
    if surrogate_path: row['delay']=None
    return row


def feature_arrays(record,features):
    c=features[str(record['cohort'])]; query=c['B']+c['A']
    return {k:np.array([query[i][k] for i in record['order']]) for k in ['words','chars','format_context']}


def curves(record,features,fit,cfg):
    values=feature_arrays(record,features); distances=np.asarray(record['distances'])
    z=(distances-np.asarray(fit['distance']['mu']))/np.asarray(fit['distance']['sigma'])
    adjusted=adjust_length(distances,np.log1p(values['words'][1:]),fit['length'])
    za=(adjusted-np.asarray(fit['length']['mu']))/np.asarray(fit['length']['sigma'])
    steps=list(range(102,257))
    result={'original':(steps,(1-np.array(record['w'])).tolist()),
            'length_endpoint':length_endpoint(values['words']),'distance_mean_endpoint':distance_endpoint(distances)}
    for k in cfg['cusum_k']:
        for prefix,source in [('cusum',z),('length_adjusted',za),('prefix_centered',prefix_center(z)),
                              ('combined',prefix_center(za))]:
            result[f'{prefix}_k{k}']=(steps,d.cusum(source[100:],k)[1].tolist())
        for name in ['reverse','shuffle17','shuffle29']:
            result[f'surrogate_{name}_k{k}']=(steps,d.cusum(surrogate(z,name)[100:],k)[1].tolist())
    d.require(len(result)==17,'Candidate count mismatch')
    return result


def load_metadata(cfg,data_root,source_cache,records):
    phase_d=ROOT/cfg['phase_d_run']; da.verify_hashes(phase_d)
    manifest=phase_d/'artifact_hashes.json'
    d.require(manifest.read_bytes()==subprocess.check_output(['git','show',cfg['phase_d_commit']+':'+manifest.relative_to(ROOT).as_posix()],cwd=ROOT),'Phase D committed artifact drift')
    cmeta=json.loads((ROOT/'stream_prada_order/results/phase_c_pilot_20261107_v1/metadata.json').read_text())
    cert=ROOT/cmeta['config']['cohort_certificate']; d.require(fb.sha(cert)==cmeta['config']['certificate_sha256'],'Certificate drift')
    cohorts=json.loads(gzip.decompress(cert.read_bytes())); fb.validate_allocation(cohorts)
    source_records,provenance=fb.load_records(data_root,source_cache)
    groups,_=fb.grouped_records(source_records,'article',set()); index={g['id']:g for g in groups}
    by_query=defaultdict(set)
    for row in source_records:
        if row['dataset']=='model_leeching': by_query[row['q']].add(row['title'])
    raw={}
    for kind in ['normal','attacker']:
        for line in (data_root/'model_leeching'/kind/'queries.jsonl').open(encoding='utf-8'):
            row=json.loads(line); text=row['query'].strip(); raw.setdefault(fb.digest(fb.norm(text)),text)
    features={}
    for cid in range(15):
        cohort=cohorts[cid]; d.check_cohort(cid)
        f={'B':[],'A':[]}
        for label in ['B','A']:
            allowed={q for g in cohort['groups'] for q in index[g]['by_dataset']['model_leeching'][label]}
            d.require(set(cohort[label])<=allowed,'Query/article source mismatch')
            for q in cohort[label]:
                text=raw[q]; titles=by_query[q]; d.require(len(titles)==1 and None not in titles,'Ambiguous article')
                f[label].append({'query_sha256':q,'words':len(text.split()),'chars':len(text),
                    'format_context':text.startswith('Given this context:'),'article':next(iter(titles))})
        titles={r['article'] for label in ['B','A'] for r in f[label]}
        d.require(len(titles)==1,'Unexpected multi-article development cohort')
        f['article']=next(iter(titles)); features[str(cid)]=f
    selected={(r['cohort'],r['key']):r for r in records}; growth={}; used={}
    cpath=ROOT/'stream_prada_order/results/phase_c_pilot_20261107_v1'
    for name in ['full_traces_calibration.jsonl.gz','full_traces_validation.jsonl.gz']:
        expected=cmeta['full_local_trace_hashes'][name]; d.require(fb.sha(cpath/name)==expected,'Growth input drift'); used[name]=expected
        with gzip.open(cpath/name,'rt',encoding='utf-8') as file:
            for line in file:
                tr=json.loads(line); key=(tr['cohort'],tr['key'])
                if key not in selected: continue
                old=selected[key]
                d.require(tr['order']==old['order'] and tr['distances']==old['distances'] and tr['w']==old['w'],'Phase C/D trace mismatch')
                g=reconstruct_growth(tr['distances'])
                d.require([idx for idx,add in zip(tr['order'],g['admitted']) if add]==tr['growing'],'Growing Set reconstruction mismatch')
                d.require(np.max(np.abs(np.array(g['thresholds'])-tr['thresholds']))<1e-14,'Growth threshold mismatch')
                growth[f'{key[0]}|{key[1]}']=g
    d.require(len(growth)==285 and sum(len(c['B'])+len(c['A']) for c in features.values())==4224,'Metadata input count mismatch')
    return features,growth,{'data_and_lookup':provenance,'selected_growth_log_hashes':used,
        'phase_d_manifest_sha256':fb.sha(manifest),'phase_c_evaluation_opened':False}


def fit_models(records,features,cfg):
    rs=[r for r in records if r['cohort'] in cfg['fit_cohorts']]
    ds=[r['distances'] for r in rs]; u=[np.log1p(feature_arrays(r,features)['words'][1:]) for r in rs]
    return {'fit_cohorts':cfg['fit_cohorts'],'distance':d.fit_distance(ds,cfg['sigma_floor']),
            'length':fit_length(ds,u,cfg['sigma_floor'])}


def associations(records,features,growth,fit,cfg):
    stream=[]; query_summary=[]
    for cid in range(15):
        f=features[str(cid)]; b=[r['words'] for r in f['B']]; a=[r['words'] for r in f['A']]
        query_summary.append({'cohort':cid,'article':f['article'],'benign_n':len(b),'attack_n':len(a),
            'benign_word_quantiles':np.quantile(b,[0,.5,.95,1]).tolist(),
            'attack_word_quantiles':np.quantile(a,[0,.5,.95,1]).tolist() if a else None,
            'benign_context_format':sum(r['format_context'] for r in f['B']),
            'attack_context_format':sum(r['format_context'] for r in f['A']),
            'benign_in_fit_support':int(in_support(np.log1p(b),fit['length']['support']).sum()),
            'attack_in_fit_support':int(in_support(np.log1p(a),fit['length']['support']).sum()),
            **overlap_counts(b,a,cfg['length_bins'])})
    for r in records:
        cid=r['cohort']; f=feature_arrays(r,features); ds=np.array(r['distances']); label=np.array(r['order'][1:])>=256
        g=growth[f'{cid}|{r["key"]}']; candidate=curves(r,features,fit,cfg)
        # Distance at query t is measured before that query's admission to Growing Set.
        row={'cohort':cid,'article':features[str(cid)]['article'],'key':r['key'],
            'rho_words_distance':rho(f['words'][1:],ds),'rho_distance_growing_before':rho(ds,g['counts'][:-1]),
            'rho_words_cusum_level':rho(f['words'][101:],candidate['cusum_k0.5'][1]),
            'rho_growing_cusum_level':rho(g['counts'][101:],candidate['cusum_k0.5'][1]),
            'final_growing_size':g['counts'][-1],'mean_words':float(f['words'].mean()),
            'max_cusum_k0_5':d.maximum(candidate['cusum_k0.5'])}
        for name,mask in [('benign',~label),('attack',label)]:
            row[name+'_n']=int(mask.sum())
            row[name+'_distance_mean']=float(ds[mask].mean()) if mask.any() else None
            row[name+'_admission_rate']=float(np.array(g['admitted'][1:])[mask].mean()) if mask.any() else None
        stream.append(row)
    groups=[]
    for cid in [12,13,14]:
        for count in [26,64,128]:
            rs=[r for r in stream if r['cohort']==cid and r['key'].startswith(str(count)+':')]
            groups.append({'cohort':cid,'attack_count':count,'article':features[str(cid)]['article'],
                'streams':len(rs),'rho_stream_mean_words_max_cusum':rho([r['mean_words'] for r in rs],[r['max_cusum_k0_5'] for r in rs]),
                **{k:float(np.mean([r[k] for r in rs if r[k] is not None])) if any(r[k] is not None for r in rs) else None
                   for k in ['rho_words_distance','rho_distance_growing_before','rho_words_cusum_level','rho_growing_cusum_level',
                             'benign_distance_mean','attack_distance_mean','benign_admission_rate','attack_admission_rate','final_growing_size']}})
    return {'query_cohorts':query_summary,'stream_features':stream,'cohort_ratio_associations':groups,
            'interpretation':'Descriptive dependence on repeated fixed paths, no population p-values or causal attribution.'}


def extend_summary(summary,rows):
    for cell in summary['cells']:
        rates=[{'cohort':p['cohort'],'rate':p['tpr_all_schedules']} for p in cell['per_cohort']]
        cell['leave_one_development_cohort_out_means']=leave_one_out(rates)
        cell['surrogate_path']=cell['candidate'].startswith('surrogate_')
        cell['endpoint_only']=cell['candidate'].endswith('_endpoint')
    summary['surrogate_comparisons']=[]
    for k in [.5,1.]:
        for alpha in [.05,.2,.4]:
            for name in ['reverse','shuffle17','shuffle29']:
                for count in [26,64,128]:
                    for order in d.original.ORDERS:
                        rs=[r for r in rows if r['has_attack'] and r['alpha']==alpha and r['attack_count']==count and r['ordering']==order]
                        base={(r['cohort'],r['permutation']):r for r in rs if r['candidate']==f'cusum_k{k}'}
                        changed=[r for r in rs if r['candidate']==f'surrogate_{name}_k{k}']
                        summary['surrogate_comparisons'].append({'k':k,'alpha':alpha,'transform':name,'attack_count':count,'ordering':order,
                            'paired':len(changed),'changed_detection':sum(r['detected']!=base[(r['cohort'],r['permutation'])]['detected'] for r in changed),
                            'mean_max_score_delta':float(np.mean([r['max_score']-base[(r['cohort'],r['permutation'])]['max_score'] for r in changed]))})
    return summary


def compute(records,features,growth,cfg,out,deadline=lambda:None):
    fit=fit_models(records,features,cfg); d.write(out/'fit_parameters.json',fit)
    cal=defaultdict(list)
    for r in records:
        if r['cohort'] not in cfg['calibration_cohorts']: continue
        for name,curve in curves(r,features,fit,cfg).items(): cal[name].append(d.maximum(curve))
        deadline()
    thresholds={name:[d.calibrate(scores,a) for a in cfg['alphas']] for name,scores in cal.items()}
    d.write(out/'thresholds.json',{'stream_maxima':cal,'thresholds':thresholds,'development_scored_at_freeze':False})
    rows=[]
    for r in records:
        if r['cohort'] not in cfg['development_cohorts']: continue
        mixed=r['key']!='benign_control'; count,perm,order=r['key'].split(':') if mixed else ('0','-1','benign_control')
        for name,curve in curves(r,features,fit,cfg).items():
            for h in thresholds[name]:
                rows.append({'cohort':r['cohort'],'key':r['key'],'candidate':name,'alpha':h['alpha'],'has_attack':mixed,
                    'attack_count':int(count),'permutation':int(perm),'ordering':order,'max_score':d.maximum(curve),
                    **metric_row(*curve,h,mixed,name.startswith('surrogate_'))})
        deadline()
    d.require(len(rows)==13923,'Incomplete candidate ledger')
    d.pc.write_table(out/'per_stream.csv.gz',rows)
    summary=extend_summary(d.summarize(rows,list(cal),cfg['alphas']),rows)
    d.write_gz(out/'summary.json.gz',summary)
    assoc=associations(records,features,growth,fit,cfg); d.write(out/'associations.json',assoc)
    return rows,summary,assoc,fit


def run(args):
    started=time.perf_counter(); cfg=json.loads((HERE/'phase_e_config_v1.json').read_text()); out=args.output
    d.require(subprocess.check_output(['git','branch','--show-current'],cwd=ROOT,text=True).strip()==d.pc.BRANCH,'Wrong branch')
    d.require(not subprocess.check_output(['git','diff','--name-only'],cwd=ROOT,text=True).strip(),'Prior tracked changes')
    d.require(not out.exists(),'Refusing to overwrite evidence')
    paths=subprocess.check_output(['git','ls-files'],cwd=ROOT,text=True).splitlines()
    baseline={p:fb.sha(ROOT/p) for p in paths if (ROOT/p).is_file()}
    sources=[Path(__file__),HERE/'phase_e_config_v1.json',HERE/'PHASE_E_PROTOCOL_TH.md',HERE/'tests/test_phase_e.py',HERE/'phase_e_plots.py']
    frozen={p.relative_to(ROOT).as_posix():fb.sha(p) for p in sources}; out.mkdir(parents=True)
    pre={'frozen_sources':frozen,'available_ram_bytes':psutil.virtual_memory().available,'gate_seconds':120,
         'python':platform.python_version(),'numpy':np.__version__,'encoder_runs':0,'gpu_required':False,
         'main_sha':subprocess.check_output(['git','rev-parse','main'],cwd=ROOT,text=True).strip(),
         'head_before_run':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()}
    d.write(out/'preflight.json',pre); status='failed_hard_gate'; reason=None; rows=[]
    def deadline(): d.require(time.perf_counter()-started<120,'Frozen 120-second gate exceeded')
    try:
        d.require(pre['available_ram_bytes']>=cfg['minimum_available_ram_bytes'],'Insufficient RAM')
        fixture={'cohort':0,'order':list(range(256)),'distances':np.linspace(.9,.5,255).tolist(),
                 'w':np.ones(155).tolist(),'w_steps':list(range(102,257))}
        ff={'0':{'B':[{'words':10,'chars':50,'format_context':False} for _ in range(256)],'A':[]}}
        fs={'mu':np.ones(255).tolist(),'sigma':np.ones(255).tolist()}
        length={'mu':fs['mu'],'sigma':fs['sigma'],'u_mean':np.ones(255).tolist(),'support':[1.,3.],'beta':0.}
        timings=[]
        for _ in range(5):
            t=time.perf_counter(); curves(fixture,ff,{'distance':fs,'length':length},cfg); timings.append(time.perf_counter()-t)
        pre.update(projected_statistic_seconds=time.perf_counter()-started+2*float(np.quantile(timings,.95))*285,
                   benchmark_p95_seconds=float(np.quantile(timings,.95)))
        pre['passed']=pre['projected_statistic_seconds']<=120; d.write(out/'preflight.json',pre)
        d.require(pre['passed'],'Resource projection failed')
        phase_d=ROOT/cfg['phase_d_run']; da.verify_hashes(phase_d)
        records=json.loads(gzip.decompress((phase_d/'development_traces.json.gz').read_bytes()))
        for r in records: d.check_cohort(r['cohort'])
        features,growth,provenance=load_metadata(cfg,args.data_root,args.source_cache,records); deadline()
        d.write_gz(out/'query_metadata.json.gz',features); d.write_gz(out/'growth_paths.json.gz',growth)
        d.write(out/'input_provenance.json',provenance)
        rows,summary,assoc,fit=compute(records,features,growth,cfg,out,deadline); deadline()
        old=ca.read_rows(phase_d/'per_stream.csv.gz')
        old_index={(int(r['cohort']),r['key'],r['candidate'],float(r['alpha'])):r for r in old}
        checked=0
        for r in rows:
            name='original' if r['candidate']=='original' else ('cusum_lower_'+r['candidate'].removeprefix('cusum_') if r['candidate'].startswith('cusum_') else None)
            if name is None: continue
            previous=old_index[(r['cohort'],r['key'],name,r['alpha'])]
            d.require(abs(float(previous['max_score'])-r['max_score'])<1e-12,'Phase D statistic drift')
            for key in ['any_alert','first_alert','prefix_alarm','eligible','detected','delay','right_censored']:
                d.require(previous[key]==('' if r[key] is None else str(r[key])),'Phase D metric drift')
            checked+=1
        d.write(out/'phase_d_parity.json',{'passed':True,'rows_checked':checked,'original_and_both_lower_k_unchanged':True})
        from phase_e_plots import plots
        plots(out,records,features,growth,fit,cfg,summary,assoc); deadline()
        status='completed_bounded_shortcut_analysis'
    except Exception as exc: reason=f'{type(exc).__name__}: {exc}'
    finally:
        unchanged=all(fb.sha(ROOT/p)==h for p,h in baseline.items()); frozen_ok=all(fb.sha(ROOT/p)==h for p,h in frozen.items())
        meta={'status':status,'reason':reason,'seconds':time.perf_counter()-started,'rows':len(rows),'config':cfg,'frozen_sources':frozen,
              'prior_tracked_files_unchanged':unchanged,'frozen_sources_unchanged':frozen_ok,
              'main_unchanged':pre['main_sha']==subprocess.check_output(['git','rev-parse','main'],cwd=ROOT,text=True).strip(),
              'process_peak_working_set_bytes':psutil.Process().memory_info().peak_wset,'encoder_runs':0,'victim_calls':0,
              'upstream_detector_reruns':0,'phase_c_evaluation_used':False,'new_data_downloaded':False,'pushed':False}
        d.write(out/'metadata.json',meta)
        d.write(out/'artifact_hashes.json',{p.name:fb.sha(p) for p in sorted(out.iterdir()) if p.is_file() and p.name!='artifact_hashes.json'})
        print(json.dumps(meta,indent=2),flush=True)
    d.require(unchanged and frozen_ok and meta['main_unchanged'],'Preservation check failed')
    return status


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-root',type=Path,default=ROOT.parent/'llm-mea/data')
    parser.add_argument('--source-cache',type=Path,default=Path.home()/'.cache/stream-prada-phase-b')
    parser.add_argument('--output',type=Path,required=True)
    raise SystemExit(0 if run(parser.parse_args())=='completed_bounded_shortcut_analysis' else 1)
