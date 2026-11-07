"""Frozen Phase C article-disjoint bounded pilot; reuse PRADA without changes."""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import io
import itertools
import json
import os
from pathlib import Path
import subprocess
import sys
import time

import numpy as np
from scipy.stats import beta

import experiment as frozen
import phase_b_feasibility as fb

ROOT=Path(__file__).resolve().parents[1]
BRANCH='experiment/stream-prada-order'
EVAL='final_test_partition_not_fresh_confirmation'


def plan_cohort(cid,nb,na,cfg):
    b=np.random.default_rng(np.random.SeedSequence([cfg['seed'],cid,0])).permutation(nb)
    a=nb+np.random.default_rng(np.random.SeedSequence([cfg['seed'],cid,1])).permutation(na)
    return {'benign_order':b,'attack_order':a}


def orders_for(plan,cid,ratio_index,permutation,cfg):
    count=cfg['attack_counts'][ratio_index]; b=plan['benign_order']; a=plan['attack_order'][:count]
    prefix=b[:cfg['prefix_length']]
    tail=b[cfg['prefix_length']:cfg['stream_length']-count]
    rng=np.random.default_rng(np.random.SeedSequence([cfg['seed'],cid,ratio_index,permutation,2]))
    return frozen.make_orders(prefix,tail,a,rng)


def score_row(trace,threshold,prefix,has_attack=True):
    first=frozen.first_alert(trace,threshold)
    early=first is not None and first<=prefix
    post=next((s for s,w in zip(trace['w_steps'],trace['w']) if s>prefix and w<1-threshold),None)
    return {'score':trace['score'],'min_w':1-trace['score'],'any_alert':first is not None,'has_attack':has_attack,
            'first_alert':first,'prefix_alarm':early,'at_risk_at_onset':not early if has_attack else None,
            'post_onset_first_detection':(not early and first is not None) if has_attack else None,
            'post_onset_crossing':post,'delay':None if not has_attack or early or first is None else first-prefix-1,
            'right_censored':(not early and first is None) if has_attack else None,'growing_size':len(trace['growing']),
            'distance_mean':float(np.mean(trace['distances']))}


def validation_passes(controls,cfg):
    return (sum(r['any_alert'] for r in controls)<=cfg['validation_max_control_alerts'] and
            sum(r['prefix_alarm'] for r in controls)<=cfg['validation_max_prefix_alerts'])


def exact_interval(k,n):
    if not n: return None
    return [0.0 if k==0 else float(beta.ppf(.025,k,n-k+1)),
            1.0 if k==n else float(beta.ppf(.975,k+1,n-k))]


def write_json_gz(path,value):
    Path(path).write_bytes(gzip.compress(json.dumps(value,separators=(',',':'),allow_nan=False).encode(),mtime=0))


def write_table(path,rows):
    if not rows: return
    stream=io.StringIO(newline=''); writer=csv.DictWriter(stream,fieldnames=list(rows[0]))
    writer.writeheader(); writer.writerows(rows)
    Path(path).write_bytes(gzip.compress(stream.getvalue().encode(),mtime=0))


def load_inputs(cfg,data_root,source_cache):
    certificate=ROOT/cfg['cohort_certificate']
    fb.require(fb.sha(certificate)==cfg['certificate_sha256'],'Phase B certificate drift')
    cohorts=json.loads(gzip.decompress(certificate.read_bytes()))
    fb.validate_allocation(cohorts)
    expected={'calibration':12,'validation':3,EVAL:8}
    fb.require({s:sum(c['split']==s for c in cohorts) for s in expected}==expected,'Unexpected split sizes')
    records,source=fb.load_records(data_root,source_cache)
    groups,_=fb.grouped_records(records,'article',set()); group_index={g['id']:g for g in groups}
    for c in cohorts:
        fb.require(all(group_index[g]['known_article'] for g in c['groups']),'Unmapped source article')
        for label in ('B','A'):
            allowed={h for g in c['groups'] for h in group_index[g]['by_dataset']['model_leeching'][label]}
            fb.require(set(c[label])<=allowed,'Query does not belong to certified article group')
    raw={}
    for kind in ('normal','attacker'):
        for line in (data_root/'model_leeching'/kind/'queries.jsonl').open(encoding='utf-8'):
            row=json.loads(line); text=row['query'].strip(); raw.setdefault(fb.digest(fb.norm(text)),text)
    for c in cohorts: fb.require(all(h in raw for h in c['B']+c['A']),'Missing actual query')
    return cohorts,raw,source


def cohort_summary(rows,cfg):
    output=[]
    for cid in sorted({r['cohort'] for r in rows}):
        for count in cfg['attack_counts']:
            for name in frozen.ORDERS:
                rs=[r for r in rows if r['cohort']==cid and r['attack_count']==count and r['ordering']==name]
                if not rs: continue
                eligible=[r for r in rs if r['at_risk_at_onset']]
                delays=[r['delay'] for r in eligible if r['delay'] is not None]
                k=sum(r['any_alert'] for r in rs)
                output.append({'cohort':cid,'split':rs[0]['split'],'attack_count':count,'ordering':name,
                    'schedules':len(rs),'any_alerts':k,'any_alert_rate':k/len(rs),
                    'conditional_mc_wilson95':frozen.wilson(k,len(rs)),
                    'prefix_alarm_schedules':sum(r['prefix_alarm'] for r in rs),'eligible_schedules':len(eligible),
                    'post_onset_detection_rate':sum(r['post_onset_first_detection'] for r in eligible)/len(eligible) if eligible else None,
                    'right_censored':sum(r['right_censored'] for r in rs),'detected_nonprefix':len(delays),
                    'median_detected_delay':float(np.median(delays)) if delays else None,
                    'mean_score':float(np.mean([r['score'] for r in rs]))})
    return output


def outer_summary(per_cohort,cfg):
    out=[]
    rng=np.random.default_rng(cfg['seed']+700)
    for split in ('validation',EVAL):
        for count in cfg['attack_counts']:
            for name in frozen.ORDERS:
                rows=[r for r in per_cohort if r['split']==split and r['attack_count']==count and r['ordering']==name]
                if not rows: continue
                values=np.array([r['any_alert_rate'] for r in rows])
                boot=values[rng.integers(0,len(values),size=(cfg['between_cohort_bootstrap_draws'],len(values)))].mean(axis=1)
                out.append({'split':split,'attack_count':count,'ordering':name,'outer_cohorts':len(rows),
                    'mean_cohort_any_alert_rate':float(values.mean()),'cohort_rate_range':[float(values.min()),float(values.max())],
                    'descriptive_outer_bootstrap95':np.quantile(boot,[.025,.975]).tolist(),
                    'warning':'Small-n reused-source cohort resampling; no population or calibration-uncertainty guarantee.'})
    return out


def run(args):
    started=time.perf_counter()
    fb.require(subprocess.check_output(['git','branch','--show-current'],cwd=ROOT,text=True).strip()==BRANCH,'Wrong branch')
    cfg=json.loads(args.config.read_text(encoding='utf-8'))
    fb.require(cfg['permutations']==100 and cfg['resource_gate_seconds']==1200,'Unexpected frozen pilot scope')
    fb.require(not args.output.exists(),'Refusing to overwrite experiment attempt')
    # The config/source must already be committed before any model or score call.
    for path in (Path(__file__),args.config):
        relative=path.resolve().relative_to(ROOT).as_posix()
        committed=subprocess.check_output(['git','show','HEAD:'+relative],cwd=ROOT)
        fb.require(hashlib.sha256(committed).hexdigest()==fb.sha(path),'Commit frozen protocol/source before execution')
    output=args.output; output.mkdir(parents=True)
    (output/'.gitignore').write_text('full_traces_*.jsonl.gz\n',encoding='utf-8',newline='\n')
    tracked=subprocess.check_output(['git','ls-files'],cwd=ROOT,text=True).splitlines()
    baseline={name:fb.sha(ROOT/name) for name in tracked}
    cohorts,raw,source=load_inputs(cfg,args.data_root,args.source_cache)
    historical=json.loads((ROOT/'stream_prada_order/results/seed20261106_25min_retry1/metadata.json').read_text())
    for name,h in historical['source_files_sha256'].items(): fb.require(fb.sha(ROOT/name)==h,'Frozen detector/helper drift')
    import torch
    import psutil
    import scipy
    import sentence_transformers
    from sentence_transformers import SentenceTransformer
    torch.set_num_threads(cfg['torch_threads'])
    fb.require(torch.cuda.is_available(),'CUDA unavailable')
    free,total=torch.cuda.mem_get_info()
    fb.require(free>=int(1.5*1024**3) and psutil.virtual_memory().available>=2*1024**3,'Resource memory preflight failed')
    fb.require(float(torch.ones(1,device='cuda').sum().cpu())==1,'CUDA operation failed')
    model_path=args.model_root/cfg['model_revision']
    for name,h in historical['model_files_sha256'].items(): fb.require(fb.sha(model_path/name)==h,'Model snapshot drift')
    torch.cuda.reset_peak_memory_stats()
    metadata={'phase':'C bounded exploratory pilot v1','status':'preflight','config':cfg,'config_sha256':fb.sha(args.config),
        'freeze_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        'source_sha256':fb.sha(__file__),'main_sha':subprocess.check_output(['git','rev-parse','main'],cwd=ROOT,text=True).strip(),
        'inputs':source,'model_files_sha256':historical['model_files_sha256'],
        'environment':{'torch':torch.__version__,'scipy':scipy.__version__,'numpy':np.__version__,
                       'sentence_transformers':sentence_transformers.__version__,'gpu':torch.cuda.get_device_name()},
        'gpu_free_before':free,'ram_available_before':psutil.virtual_memory().available,
        'maximum_single_cohort_matrix_bytes':384*384*4,'evaluation_encoded':False,'evaluation_scored':False,
        'cohort_group_counts':[{'cohort':i,'split':c['split'],'source_groups':len(c['groups'])} for i,c in enumerate(cohorts)],
        'caveat':'Exploratory reused articles. Calibration/validation have one article per cohort; 7/8 evaluation cohorts combine two articles. No iid-population/FPR guarantee.'}
    frozen.json_write(output/'metadata.json',metadata)
    os.environ['HF_HUB_OFFLINE']='1'; os.environ['TRANSFORMERS_OFFLINE']='1'
    model=SentenceTransformer(str(model_path),device='cuda',local_files_only=True); model.eval()
    for parameter in model.parameters(): parameter.requires_grad_(False)
    fb.require(model.max_seq_length==cfg['max_seq_length'],'Encoder truncation drift')
    matrices={}; vectors={}; plans={}; controls=[]; rows=[]; differences=[]; timings=[]; parity=[]; examples={}
    full_logs={split:gzip.open(output/f'full_traces_{split}.jsonl.gz','wt',encoding='utf-8',newline='\n')
               for split in ('calibration','validation','evaluation')}

    def deadline():
        fb.require(time.perf_counter()-started<cfg['resource_gate_seconds'],'1200-second gate reached; stop for approval')

    def encode_stage(ids,label):
        deadline(); hashes=[h for cid in ids for h in cohorts[cid]['B']+cohorts[cid]['A']]
        before=time.perf_counter()
        with torch.inference_mode():
            z=model.encode([raw[h] for h in hashes],batch_size=cfg['encode_batch_size'],normalize_embeddings=True,
                           convert_to_numpy=True,show_progress_bar=True)
        fb.require(np.isfinite(z).all() and np.allclose(np.linalg.norm(z,axis=1),1,atol=1e-5),'Invalid embeddings')
        frozen.json_write(output/f'embedding_{label}.json',{'queries':len(hashes),'seconds':time.perf_counter()-before,
            'query_order_sha256':fb.digest('\0'.join(hashes)),'raw_text_order_sha256':fb.digest('\0'.join(raw[h] for h in hashes)),
            'embedding_sha256':hashlib.sha256(z.tobytes()).hexdigest()})
        cursor=0
        for cid in ids:
            n=len(cohorts[cid]['B'])+len(cohorts[cid]['A']); part=z[cursor:cursor+n]; cursor+=n
            vectors[cid]=part; tensor=torch.from_numpy(part); matrices[cid]=torch.cdist(tensor,tensor).numpy()
            plans[cid]=plan_cohort(cid,len(cohorts[cid]['B']),len(cohorts[cid]['A']),cfg)
        deadline()

    def score(cid,order,split,key,threshold):
        deadline(); begin=time.perf_counter(); trace=frozen.trace(matrices[cid],order)
        elapsed=time.perf_counter()-begin; timings.append(elapsed)
        kept=[len(frozen.base.trim_outliers_3sigma(np.asarray(trace['distances'][:step-1],dtype=float))) for step in trace['w_steps']]
        record={'cohort':cid,'key':key,'order':order.tolist(),**trace,'retained_samples':kept}
        full_logs[split].write(json.dumps(record,separators=(',',':'),allow_nan=False)+'\n')
        row={'cohort':cid,'split':cohorts[cid]['split'],**score_row(trace,threshold,cfg['prefix_length'],has_attack=key not in ('benign','benign_control')),
             'runtime_seconds':elapsed,'order_sha256':hashlib.sha256(order.astype('<i8').tobytes()).hexdigest()}
        return trace,row,record

    def check_parity(cid,order,actual,threshold):
        import prada_stream_detector as reference
        reference.np=np; reference.torch=torch; reference.base.np=np
        expected=reference.prada_stream_trace(vectors[cid][order],'l2','cpu',1-threshold,100,5000,1,True,False,np.random.default_rng(0))
        error=float(np.max(np.abs(np.array(actual['w'])-expected[4])))
        fb.require(error<=cfg['parity_w_absolute_tolerance'] and len(actual['growing'])==expected[3], 'Reference trajectory/growth parity failed')
        fb.require(frozen.first_alert(actual,threshold)==(None if expected[1]<0 else expected[1]),'Reference first-alert parity failed')
        parity.append({'cohort':cid,'maximum_w_error':error,'growing_size':expected[3],'first_alert':expected[1]})

    def mixed(cid,permutations,threshold):
        split='validation' if cohorts[cid]['split']=='validation' else 'evaluation'
        for permutation in permutations:
            for ri,count in enumerate(cfg['attack_counts']):
                traces={}
                for name,order in orders_for(plans[cid],cid,ri,permutation,cfg).items():
                    tr,row,record=score(cid,order,split,f'{count}:{permutation}:{name}',threshold)
                    row.update(attack_count=count,attack_fraction=count/cfg['stream_length'],permutation=permutation,ordering=name)
                    rows.append(row); traces[name]=tr
                    if permutation==0: examples.setdefault(str(cid),[]).append(record)
                for a,b in itertools.combinations(frozen.ORDERS,2):
                    x,y=traces[a],traces[b]
                    differences.append({'cohort':cid,'split':cohorts[cid]['split'],'attack_count':count,
                        'permutation':permutation,'a':a,'b':b,'changed_alert':frozen.alert(x,threshold)!=frozen.alert(y,threshold),
                        'score_delta_b_minus_a':y['score']-x['score'],
                        'growing_symmetric_difference':len(set(x['growing'])^set(y['growing'])),
                        'distance_mae':float(np.mean(np.abs(np.array(x['distances'])-y['distances']))),
                        'w_mae':float(np.mean(np.abs(np.array(x['w'])-y['w'])))})

    status='failed'; threshold=None; reason=None
    try:
        cal_ids=[i for i,c in enumerate(cohorts) if c['split']=='calibration']
        val_ids=[i for i,c in enumerate(cohorts) if c['split']=='validation']
        eval_ids=[i for i,c in enumerate(cohorts) if c['split']==EVAL]
        encode_stage(cal_ids+val_ids,'calibration_validation')
        calibration=[]
        for cid in cal_ids:
            order=plans[cid]['benign_order']; tr,row,record=score(cid,order,'calibration','benign',1.0)
            calibration.append({'cohort':cid,'score':tr['score']})
            write_json_gz(output/f'calibration_trace_{cid:02d}.json.gz',record)
            if cid==cal_ids[0]: check_parity(cid,order,tr,.01)
        threshold=float(np.percentile([r['score'] for r in calibration],95,method='linear'))
        frozen.json_write(output/'calibration.json',{'threshold':threshold,'delta_w':1-threshold,'cohorts':calibration,
            'strict_exceedances':sum(r['score']>threshold for r in calibration),'fitted_on':'12 calibration cohorts only'})
        for cid in val_ids:
            tr,row,record=score(cid,plans[cid]['benign_order'],'validation','benign_control',threshold)
            controls.append(row); write_json_gz(output/f'control_trace_{cid:02d}.json.gz',record)
            check_parity(cid,plans[cid]['benign_order'],tr,threshold)
        pilot_start=len(timings)
        for cid in val_ids: mixed(cid,range(cfg['validation_pilot_permutations']),threshold)
        pilot_times=timings[pilot_start:]
        remaining=3*len(cfg['attack_counts'])*cfg['permutations']*(len(val_ids)+len(eval_ids))-len(rows)+len(eval_ids)
        projected=time.perf_counter()-started+cfg['resource_safety_factor']*float(np.quantile(pilot_times,.95))*remaining
        resource_pass=projected<=cfg['resource_gate_seconds']
        frozen.json_write(output/'resource_gate.json',{'passed':resource_pass,'projected_total_seconds':projected,
            'gate_seconds':cfg['resource_gate_seconds'],'pilot_p95_stream_seconds':float(np.quantile(pilot_times,.95)),
            'pilot_streams':len(pilot_times),'remaining_streams':remaining,'safety_factor':cfg['resource_safety_factor']})
        control_gate=validation_passes(controls,cfg)
        frozen.json_write(output/'validation_gate.json',{'passed':control_gate,'control_alerts':sum(r['any_alert'] for r in controls),
            'prefix_alerts':sum(r['prefix_alarm'] for r in controls),'controls':len(controls),
            'rule':'zero control alarms and zero pre-attack prefix alarms; frozen before scoring',
            'evaluation_encoded_at_gate':False,'evaluation_scored_at_gate':False})
        if not resource_pass:
            status='blocked_resource_projection'; reason='Projected runtime exceeds frozen 20-minute gate; no scope reduction.'
        elif not control_gate:
            status='stopped_validation_failure'; reason='Frozen validation gate failed; no evaluation encoding or scoring.'
        else:
            for cid in val_ids: mixed(cid,range(cfg['validation_pilot_permutations'],cfg['permutations']),threshold)
            encode_stage(eval_ids,'evaluation'); metadata['evaluation_encoded']=True
            for cid in eval_ids:
                tr,row,record=score(cid,plans[cid]['benign_order'],'evaluation','benign_control',threshold)
                controls.append(row); write_json_gz(output/f'control_trace_{cid:02d}.json.gz',record)
                check_parity(cid,plans[cid]['benign_order'],tr,threshold)
                mixed(cid,range(cfg['permutations']),threshold)
                metadata['evaluation_scored']=True
                print(f'Completed evaluation cohort {cid}; elapsed={time.perf_counter()-started:.1f}s',flush=True)
            status='completed_bounded_pilot'
    except Exception as exc:
        reason=f'{type(exc).__name__}: {exc}'; status='failed_hard_gate'
    finally:
        for f in full_logs.values(): f.close()
        frozen.json_write(output/'parity.json',parity)
        frozen.json_write(output/'controls.json',controls)
        for cid in sorted({r['cohort'] for r in rows}):
            write_table(output/f'scores_cohort_{cid:02d}.csv.gz',[r for r in rows if r['cohort']==cid])
            write_table(output/f'differences_cohort_{cid:02d}.csv.gz',[r for r in differences if r['cohort']==cid])
        for cid,records in examples.items(): write_json_gz(output/f'example_traces_cohort_{int(cid):02d}.json.gz',records)
        per_cohort=cohort_summary(rows,cfg)
        controls_summary=[]
        for split in ('validation',EVAL):
            rs=[r for r in controls if r['split']==split]
            k=sum(r['any_alert'] for r in rs)
            controls_summary.append({'split':split,'cohorts':len(rs),'any_alerts':k,
                'fpr':k/len(rs) if rs else None,'cohort_binomial95':exact_interval(k,len(rs)),
                'prefix_alarm_cohorts':sum(r['prefix_alarm'] for r in rs)})
        summary={'status':status,'reason':reason,'threshold':threshold,'control_summary':controls_summary,
            'per_cohort':per_cohort,'outer_summary':outer_summary(per_cohort,cfg),
            'mixed_streams_scored':len(rows),'paired_comparisons':len(differences),
            'evaluation_rates_unmeasured':not metadata['evaluation_scored'],
            'caveats':['Reused article sources; exploratory protocol pilot only.',
                       'Calibration n=12 and evaluation n=8 do not establish population FPR 5%.',
                       'Source-count composition differs between calibration and evaluation cohorts.',
                       'Permutations are conditional repeated measurements, not independent outer cohorts.']}
        frozen.json_write(output/'summary.json',summary)
        metadata.update(status=status,reason=reason,total_seconds=time.perf_counter()-started,
            process_peak_working_set_bytes=psutil.Process().memory_info().peak_wset,
            gpu_peak_allocated_bytes=torch.cuda.max_memory_allocated(),gpu_peak_reserved_bytes=torch.cuda.max_memory_reserved(),
            prior_tracked_files_unchanged=all(fb.sha(ROOT/name)==h for name,h in baseline.items()),
            full_local_trace_hashes={p.name:fb.sha(p) for p in output.glob('full_traces_*.jsonl.gz')})
        frozen.json_write(output/'metadata.json',metadata)
        frozen.json_write(output/'artifact_hashes.json',{p.name:fb.sha(p) for p in sorted(output.iterdir())
            if p.is_file() and not p.name.startswith('full_traces_') and p.name!='artifact_hashes.json'})
        print(json.dumps({'status':status,'reason':reason,'seconds':metadata['total_seconds'],
                          'mixed_streams':len(rows),'controls':controls_summary}),flush=True)
    fb.require(metadata['prior_tracked_files_unchanged'],'Previous tracked files were altered')
    return summary


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config',type=Path,default=Path(__file__).with_name('phase_c_config_v1.json'))
    parser.add_argument('--data-root',type=Path,default=ROOT.parent/'llm-mea/data')
    parser.add_argument('--source-cache',type=Path,default=Path.home()/'.cache/stream-prada-phase-b')
    parser.add_argument('--model-root',type=Path,default=Path.home()/'.cache/huggingface/hub/models--BAAI--bge-small-en-v1.5/snapshots')
    parser.add_argument('--output',type=Path,required=True)
    run(parser.parse_args())
