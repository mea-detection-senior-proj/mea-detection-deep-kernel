"""Isolated sequential-statistic development pilot on frozen Phase C distances."""
from __future__ import annotations

import argparse
import gzip
import hashlib
import itertools
import json
import math
from pathlib import Path
import platform
import subprocess
import time

import numpy as np
import psutil
import scipy
from scipy.stats import shapiro

import experiment as original
import phase_c_runner as pc

ROOT=Path(__file__).resolve().parents[1]
HERE=Path(__file__).resolve().parent


def require(condition,message):
    if not condition: raise ValueError(message)


def check_cohort(cid):
    require(0<=cid<=14,'Phase C evaluation cohort is prohibited')


def source_matches(raw,git_blob,historical_sha):
    return (hashlib.sha256(raw).hexdigest()==historical_sha and
            raw.replace(b'\r\n',b'\n')==git_blob.replace(b'\r\n',b'\n'))


def rolling(distances,length):
    d=np.asarray(distances,dtype=float)
    require(d.shape==(255,) and np.isfinite(d).all(),'Invalid distance history')
    require(3<=length<=100,'History exceeds predeclared warmup')
    scores=[]
    for end in range(101,256):
        values=original.base.trim_outliers_3sigma(d[end-length:end])
        require(len(values)>=3 and np.ptp(values)>0,'Degenerate rolling sample')
        w=float(shapiro(values).statistic)
        require(np.isfinite(w),'Nonfinite rolling W')
        scores.append(1-w)
    return list(range(102,257)),scores


def cusum(z,k):
    z=np.asarray(z,dtype=float)
    require(np.isfinite(z).all() and k>0,'Invalid CUSUM input')
    up=[]; low=[]; plus=minus=0.
    for value in z:
        plus=max(0.,plus+value-k); minus=max(0.,minus-value-k)
        up.append(plus); low.append(minus)
    return np.array(up),np.array(low)


def fit_distance(histories,floor):
    data=np.asarray(histories,dtype=float)
    require(data.ndim==2 and data.shape[0]>=2 and data.shape[1]==255 and np.isfinite(data).all() and floor>0,'Invalid fit data')
    return {'mu':data.mean(axis=0).tolist(),'sigma':np.maximum(data.std(axis=0,ddof=1),floor).tolist()}


def curves(record,fit,cfg):
    steps=list(range(102,257)); d=np.asarray(record['distances'])
    require(d.shape==(255,) and record['w_steps']==steps,'Unexpected horizon/warmup')
    result={'original':(steps,(1-np.array(record['w'])).tolist())}
    for length in cfg['rolling_lengths']: result[f'rolling_{length}']=rolling(d,length)
    z=((d-np.array(fit['mu']))/np.array(fit['sigma']))[100:]
    for k in cfg['cusum_k']:
        up,low=cusum(z,k)
        for side,values in [('upper',up),('lower',low),('two_sided',np.maximum(up,low))]:
            result[f'cusum_{side}_k{k}']=(steps,values.tolist())
    return result


def maximum(curve):
    steps,values=curve
    require(len(steps)==len(values)>0 and np.isfinite(values).all(),'Invalid statistic path')
    return float(max(values))


def calibrate(scores,alpha):
    values=np.asarray(scores,dtype=float)
    require(0<alpha<1 and len(values)>0 and np.isfinite(values).all(),'Invalid calibration')
    rank=math.ceil((len(values)+1)*(1-alpha)); finite=rank<=len(values)
    h=float(np.sort(values)[rank-1]) if finite else None
    return {'alpha':alpha,'n':len(values),'rank':rank,'finite':finite,'threshold':h,
            'strict_calibration_exceedances':int(np.sum(values>h)) if finite else 0}


def crossing(steps,values,threshold,has_attack=True):
    first=next((int(s) for s,v in zip(steps,values) if threshold['finite'] and v>threshold['threshold']),None)
    early=first is not None and first<=110
    return {'any_alert':first is not None,'first_alert':first,'prefix_alarm':early,
            'eligible':not early if has_attack else None,
            'detected':not early and first is not None if has_attack else None,
            'delay':first-111 if has_attack and not early and first is not None else None,
            'right_censored':not early and first is None if has_attack else None}


def match_screen(base_controls,variant_controls,base_prefix,variant_prefix):
    return base_controls==variant_controls and base_prefix==variant_prefix==0


def write(path,value): original.json_write(path,value)


def write_gz(path,value):
    path.write_bytes(gzip.compress(json.dumps(value,separators=(',',':'),allow_nan=False).encode(),mtime=0))


def parity(record,tolerance):
    require(len(record['distances'])==255,'Missing upstream distances')
    ws=[]
    for end in range(101,256):
        values=original.base.trim_outliers_3sigma(np.array(record['distances'][:end],dtype=float))
        require(len(values)>=3 and np.ptp(values)>0,'Degenerate upstream sample')
        ws.append(float(shapiro(values).statistic))
    error=float(np.max(np.abs(np.array(ws)-record['w'])))
    require(error<=tolerance,'Upstream cumulative W parity failed')
    require(abs(record['score']-(1-min(record['w'])))<1e-14,'Upstream score mismatch')
    return error


def load_development(cfg):
    source=ROOT/cfg['input_run']; commit=cfg['phase_c_commit']
    for name in ['metadata.json','artifact_hashes.json']:
        require((source/name).read_bytes()==subprocess.check_output(['git','show',f'{commit}:{cfg["input_run"]}/{name}'],cwd=ROOT),'Upstream metadata drift')
    meta=json.loads((source/'metadata.json').read_text())
    historical_path=ROOT/'stream_prada_order/results/seed20261106_25min_retry1/metadata.json'
    require(historical_path.read_bytes()==subprocess.check_output(['git','show',f'{commit}:{historical_path.relative_to(ROOT).as_posix()}'],cwd=ROOT),'Historical provenance drift')
    historical=json.loads(historical_path.read_text())['source_files_sha256']
    for relative in ['stream_prada_order/experiment.py','stream_prada_order/phase_c_runner.py',
                     'PRADA/prada_detector.py','PRADA/prada_stream_detector.py','pilot/protocol.py',meta['config']['cohort_certificate']]:
        raw=(ROOT/relative).read_bytes(); blob=subprocess.check_output(['git','show',f'{commit}:{relative}'],cwd=ROOT)
        expected=historical.get(relative.replace('/','\\'))
        require(source_matches(raw,blob,expected) if expected else raw==blob,f'Frozen source drift: {relative}')
    certificate=ROOT/meta['config']['cohort_certificate']
    require(original.sha(certificate)==meta['config']['certificate_sha256'],'Cohort certificate drift')
    cohorts=json.loads(gzip.decompress(certificate.read_bytes()))
    pc.fb.validate_allocation(cohorts)
    records=[]; used_hashes={}
    for name in ['full_traces_calibration.jsonl.gz','full_traces_validation.jsonl.gz']:
        expected=meta['full_local_trace_hashes'][name]
        require(original.sha(source/name)==expected,'Full input log hash mismatch')
        used_hashes[name]=expected
        with gzip.open(source/name,'rt',encoding='utf-8') as f:
            for line in f:
                tr=json.loads(line); cid=tr['cohort']; check_cohort(cid)
                require(cid in (cfg['fit_cohorts']+cfg['calibration_cohorts'] if 'calibration' in name else cfg['validation_cohorts']),'Unexpected input split')
                is_control=tr['key'] in ('benign','benign_control')
                if not is_control:
                    count,perm,ordering=tr['key'].split(':'); count=int(count); perm=int(perm)
                    if perm>=cfg['permutations']: continue
                plan=pc.plan_cohort(cid,len(cohorts[cid]['B']),len(cohorts[cid]['A']),meta['config'])
                expected_order=plan['benign_order'] if is_control else pc.orders_for(plan,cid,cfg['attack_counts'].index(count),perm,meta['config'])[ordering]
                require(np.array_equal(tr['order'],expected_order),'Frozen membership/order mismatch')
                records.append({k:tr[k] for k in ['cohort','key','order','distances','w','w_steps','score']})
    keys={(r['cohort'],r['key']) for r in records}
    require(len(keys)==len(records)==285,'Development input count/duplicate mismatch')
    for cid in cfg['validation_cohorts']:
        expected={(cid,'benign_control')}|{(cid,f'{n}:{p}:{o}') for n in cfg['attack_counts'] for p in range(10) for o in original.ORDERS}
        require(expected<=keys,'Missing paired development schedules')
    return records,{'selected_full_log_hashes':used_hashes,'upstream_metadata_sha256':original.sha(source/'metadata.json'),
                    'model':meta['config']['model'],'model_revision':meta['config']['model_revision'],
                    'certificate_sha256':original.sha(certificate),'phase_c_evaluation_logs_opened':False}


def summarize(rows,names,alphas):
    controls=[]; cells=[]; order_pairs=[]; comparisons=[]
    for alpha in alphas:
        for name in names:
            selected=[r for r in rows if r['candidate']==name and r['alpha']==alpha]
            control=sorted([r for r in selected if not r['has_attack']],key=lambda r:r['cohort'])
            vector=[r['any_alert'] for r in control]; k=sum(vector)
            controls.append({'candidate':name,'alpha':alpha,'cohorts':3,'false_alarms':k,'fpr':k/3,
                'alarm_vector':vector,'exact_two_sided95':pc.exact_interval(k,3),
                'one_sided95_upper':float(pc.beta.ppf(.95,k+1,3-k)) if k<3 else 1.})
            for count in [26,64,128]:
                for order in original.ORDERS:
                    rs=[r for r in selected if r['has_attack'] and r['attack_count']==count and r['ordering']==order]
                    delays=[r['delay'] for r in rs if r['delay'] is not None]; eligible=sum(r['eligible'] for r in rs); detected=sum(r['detected'] for r in rs)
                    per=[]
                    for cid in [12,13,14]:
                        cr=[r for r in rs if r['cohort']==cid]; cd=sum(r['detected'] for r in cr)
                        per.append({'cohort':cid,'schedules':len(cr),'detections':cd,'tpr_all_schedules':cd/len(cr),
                            'prefix_alarms':sum(r['prefix_alarm'] for r in cr),'eligible':sum(r['eligible'] for r in cr),
                            'conditional_mc_wilson95':original.wilson(cd,len(cr))})
                    cells.append({'candidate':name,'alpha':alpha,'attack_count':count,'ordering':order,'outer_cohorts':3,
                        'schedules':len(rs),'any_alerts':sum(r['any_alert'] for r in rs),'pre_attack_alarms':sum(r['prefix_alarm'] for r in rs),
                        'eligible':eligible,'detections':detected,'tpr_all_schedules':detected/len(rs),
                        'tpr_eligible':detected/eligible if eligible else None,'right_censored':sum(r['right_censored'] for r in rs),
                        'median_detected_delay':float(np.median(delays)) if delays else None,'delay_n':len(delays),'per_cohort':per})
                index={(r['cohort'],r['permutation'],r['ordering']):r for r in selected if r['has_attack'] and r['attack_count']==count}
                for a,b in itertools.combinations(original.ORDERS,2):
                    for metric in ['any_alert','detected']:
                        changes=[int(index[(cid,p,a)][metric]!=index[(cid,p,b)][metric]) for cid in [12,13,14] for p in range(10)]
                        order_pairs.append({'candidate':name,'alpha':alpha,'attack_count':count,'a':a,'b':b,'metric':metric,
                            'changed':sum(changes),'pairs':len(changes),'fraction':float(np.mean(changes))})
        base_control=next(c for c in controls if c['candidate']=='original' and c['alpha']==alpha)
        for name in names:
            if name=='original': continue
            control=next(c for c in controls if c['candidate']==name and c['alpha']==alpha)
            for cell in [c for c in cells if c['candidate']==name and c['alpha']==alpha]:
                base=next(c for c in cells if c['candidate']=='original' and c['alpha']==alpha and c['attack_count']==cell['attack_count'] and c['ordering']==cell['ordering'])
                comparisons.append({'candidate':name,'alpha':alpha,'attack_count':cell['attack_count'],'ordering':cell['ordering'],
                    'tpr_difference':cell['tpr_all_schedules']-base['tpr_all_schedules'],
                    'empirical_control_vector_match':base_control['alarm_vector']==control['alarm_vector'],
                    'passes_empirical_control_and_prefix_screen':match_screen(base_control['alarm_vector'],control['alarm_vector'],base['pre_attack_alarms'],cell['pre_attack_alarms']),
                    'warning':'Descriptive paired development screen only; n=3 does not establish matched population FPR or improvement.'})
    return {'controls':controls,'cells':cells,'order_sensitivity':order_pairs,'baseline_comparisons':comparisons}


def plots(summary,out):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    controls=summary['controls']; cells=summary['cells']; names=list(dict.fromkeys(c['candidate'] for c in controls))
    fig,axes=plt.subplots(1,2,figsize=(14,5),constrained_layout=True)
    for j,alpha in enumerate([.2,.4]):
        cs=[c for c in controls if c['alpha']==alpha]
        axes[0].bar(np.arange(len(names))+(j-.5)*.35,[c['fpr'] for c in cs],width=.35,label=f'alpha={alpha}')
    axes[0].set(xticks=range(len(names)),xticklabels=names,ylabel='Benign-control FPR (3 cohorts)',ylim=(0,1),title='Diagnostic operating levels; not 5% FPR control')
    axes[0].tick_params(axis='x',rotation=75); axes[0].legend()
    for name in names:
        cs=[c for c in cells if c['candidate']==name and c['alpha']==.2 and c['attack_count']==128]
        axes[1].plot(range(3),[c['tpr_all_schedules'] for c in cs],marker='o',label=name)
    axes[1].set(xticks=range(3),xticklabels=original.ORDERS,ylabel='Eligible first detection / all schedules',ylim=(-.02,1.02),title='50% attack at nominal alpha=0.20 (development only)')
    axes[1].legend(fontsize=7)
    fig.suptitle('Phase D: 3 reused outer cohorts; 10 schedules/cohort; compare FPR and prefix alarms together')
    fig.savefig(out/'phase_d_comparison.png',dpi=150); plt.close(fig)


def run(args):
    started=time.perf_counter(); cfg=json.loads(args.config.read_text(encoding='utf-8')); out=args.output
    require(subprocess.check_output(['git','branch','--show-current'],cwd=ROOT,text=True).strip()==pc.BRANCH,'Wrong branch')
    require(not subprocess.check_output(['git','diff','--name-only'],cwd=ROOT,text=True).strip(),'Tracked changes before run')
    require(not out.exists(),'Refusing to overwrite prior attempt')
    expected=json.loads((HERE/'phase_d_config_v1.json').read_text())
    require(cfg==expected and cfg['fit_cohorts']==[0,1,2,3] and cfg['calibration_cohorts']==list(range(4,12))
            and cfg['validation_cohorts']==[12,13,14] and cfg['permutations']==10 and cfg['resource_gate_seconds']==120,'Unexpected pilot scope')
    tracked=subprocess.check_output(['git','ls-files'],cwd=ROOT,text=True).splitlines()
    prior={p:original.sha(ROOT/p) for p in tracked if (ROOT/p).is_file()}
    sources=[Path(__file__),args.config,HERE/'PHASE_D_DESIGN_TH.md',HERE/'tests/test_phase_d.py']
    frozen={p.relative_to(ROOT).as_posix():original.sha(p) for p in sources}
    main_sha=subprocess.check_output(['git','rev-parse','main'],cwd=ROOT,text=True).strip()
    out.mkdir(parents=True)
    preflight={'frozen_sources':frozen,'available_ram_bytes':psutil.virtual_memory().available,'minimum_ram_bytes':cfg['minimum_available_ram_bytes'],
        'resource_gate_seconds':120,'encoder_runs':0,'gpu_required':False,'python':platform.python_version(),
        'numpy':np.__version__,'scipy':scipy.__version__,'cpu':platform.processor(),'main_sha':main_sha,
        'head_before_run':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()}
    write(out/'preflight.json',preflight)
    rows=[]; status='failed_hard_gate'; reason=None
    def deadline(): require(time.perf_counter()-started<120,'Frozen 120-second deadline exceeded')
    try:
        require(preflight['available_ram_bytes']>=cfg['minimum_available_ram_bytes'],'Insufficient RAM')
        fixture={'distances':np.random.default_rng(20261107).normal(1,.1,255).tolist(),'w':np.ones(155).tolist(),'w_steps':list(range(102,257))}
        fixed={'mu':np.ones(255).tolist(),'sigma':np.ones(255).tolist()}; timings=[]
        for _ in range(5):
            before=time.perf_counter(); curves(fixture,fixed,cfg); timings.append(time.perf_counter()-before)
        projected=time.perf_counter()-started+2*float(np.quantile(timings,.95))*285
        preflight.update(projected_statistic_seconds=projected,benchmark_p95=float(np.quantile(timings,.95)),
                         projection_covers='285 all-candidate statistic paths; full attempt also bounded by deadline',passed=projected<=120)
        write(out/'preflight.json',preflight)
        require(preflight['passed'],'Resource projection exceeds frozen gate')
        records,provenance=load_development(cfg); deadline(); write(out/'input_provenance.json',provenance)
        write_gz(out/'development_traces.json.gz',records)
        fit_records=[r for r in records if r['cohort'] in cfg['fit_cohorts']]
        require(len(fit_records)==4,'Incorrect fit count')
        fit=fit_distance([r['distances'] for r in fit_records],cfg['sigma_floor'])
        write(out/'distance_fit.json',{'fit_cohorts':cfg['fit_cohorts'],'sigma_floor':cfg['sigma_floor'],**fit})
        errors=[]
        for r in records:
            errors.append(parity(r,cfg['parity_w_tolerance'])); deadline()
        write(out/'upstream_parity.json',{'traces':len(errors),'max_w_abs_error':max(errors),'passed':True,
            'scope':'Recompute cumulative W from hashed saved BGE distance paths; upstream encoder/Growing Set inherited unchanged.'})
        cal={}
        for r in records:
            if r['cohort'] not in cfg['calibration_cohorts']: continue
            for name,curve in curves(r,fit,cfg).items(): cal.setdefault(name,[]).append(maximum(curve))
            deadline()
        thresholds={name:[calibrate(scores,a) for a in cfg['alphas']] for name,scores in cal.items()}
        write(out/'thresholds.json',{'calibration_cohorts':cfg['calibration_cohorts'],'stream_maxima':cal,'thresholds':thresholds,
            'validation_scored_at_freeze':False,'parameter_selection':'none'})
        for r in records:
            if r['cohort'] not in cfg['validation_cohorts']: continue
            is_attack=r['key']!='benign_control'
            count,perm,order=r['key'].split(':') if is_attack else ('0','-1','benign_control')
            for name,curve in curves(r,fit,cfg).items():
                for threshold in thresholds[name]:
                    row={'cohort':r['cohort'],'key':r['key'],'attack_count':int(count),'permutation':int(perm),'ordering':order,
                        'has_attack':is_attack,'candidate':name,'alpha':threshold['alpha'],'max_score':maximum(curve),
                        **crossing(*curve,threshold,has_attack=is_attack)}
                    if name=='original':
                        h=threshold['threshold'] if threshold['finite'] else 2.
                        require(original.first_alert(r,h)==row['first_alert'],'Original strict first-alert parity failed')
                    rows.append(row)
            deadline()
        require(len(rows)==8190,'Incomplete candidate/operating-point ledger')
        pc.write_table(out/'per_stream.csv.gz',rows)
        summary=summarize(rows,list(cal),cfg['alphas']); write(out/'summary.json',summary)
        plots(summary,out); deadline(); status='completed_bounded_development_pilot'
    except Exception as exc:
        reason=f'{type(exc).__name__}: {exc}'
    finally:
        unchanged=all(original.sha(ROOT/p)==h for p,h in prior.items())
        freeze_unchanged=all(original.sha(ROOT/p)==h for p,h in frozen.items())
        metadata={'status':status,'reason':reason,'seconds':time.perf_counter()-started,'rows':len(rows),'config':cfg,
            'frozen_sources':frozen,'frozen_sources_unchanged':freeze_unchanged,'prior_tracked_files_unchanged':unchanged,
            'main_unchanged':subprocess.check_output(['git','rev-parse','main'],cwd=ROOT,text=True).strip()==main_sha,
            'process_peak_working_set_bytes':psutil.Process().memory_info().peak_wset,'encoder_runs':0,
            'upstream_detector_reruns':0,'new_sequential_statistics_evaluated':True,'phase_c_evaluation_used':False,
            'pushed':False,'new_detector_is_experimental':True}
        write(out/'metadata.json',metadata)
        write(out/'artifact_hashes.json',{p.name:original.sha(p) for p in sorted(out.iterdir()) if p.is_file() and p.name!='artifact_hashes.json'})
        print(json.dumps(metadata,indent=2),flush=True)
    require(unchanged and freeze_unchanged and metadata['main_unchanged'],'Preservation check failed')
    return status


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config',type=Path,default=HERE/'phase_d_config_v1.json')
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    result=run(args)
    raise SystemExit(0 if result=='completed_bounded_development_pilot' else 1)
