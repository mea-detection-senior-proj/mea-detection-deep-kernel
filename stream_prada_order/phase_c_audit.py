"""Audit Phase C saved logs/tables and render diagnostics; no model/detector run."""
import argparse
import csv
import gzip
import hashlib
import io
import json
from pathlib import Path
import subprocess

import numpy as np

import phase_c_runner as pc
import phase_b_feasibility as fb


def read_rows(path):
    return list(csv.DictReader(io.StringIO(gzip.decompress(path.read_bytes()).decode())))


def bool_value(value):
    fb.require(value in ('True','False'),'Invalid Boolean field')
    return value=='True'


def audit(path,full_logs=True):
    m=json.loads((path/'metadata.json').read_text()); cfg=m['config']; summary=json.loads((path/'summary.json').read_text())
    for name,h in json.loads((path/'artifact_hashes.json').read_text()).items():
        fb.require(fb.sha(path/name)==h,f'Artifact mismatch: {name}')
    fb.require(fb.sha(pc.ROOT/'stream_prada_order/phase_c_runner.py')==m['source_sha256'],'Executed runner drift')
    fb.require(fb.sha(pc.ROOT/'stream_prada_order/phase_c_config_v1.json')==m['config_sha256'],'Config drift')
    for name,expected in [('stream_prada_order/phase_c_runner.py',m['source_sha256']),('stream_prada_order/phase_c_config_v1.json',m['config_sha256'])]:
        data=subprocess.check_output(['git','show',m['freeze_commit']+':'+name],cwd=pc.ROOT)
        fb.require(hashlib.sha256(data).hexdigest()==expected,'Run does not match freeze commit')
    cert=pc.ROOT/cfg['cohort_certificate']; fb.require(fb.sha(cert)==cfg['certificate_sha256'],'Certificate drift')
    cohorts=json.loads(gzip.decompress(cert.read_bytes())); fb.validate_allocation(cohorts)
    cal=json.loads((path/'calibration.json').read_text()); threshold=cal['threshold']
    fb.require(len(cal['cohorts'])==12,'Incomplete calibration')
    fb.require(abs(threshold-np.percentile([r['score'] for r in cal['cohorts']],95,method='linear'))<1e-14,'Threshold mismatch')
    fb.require(cal['strict_exceedances']==sum(r['score']>threshold for r in cal['cohorts']),'Calibration count mismatch')
    controls=json.loads((path/'controls.json').read_text())
    fb.require(all(not r['has_attack'] and r['post_onset_first_detection'] is None and r['delay'] is None for r in controls),
               'Benign control mislabeled as attack detection')
    val=[r for r in controls if r['split']=='validation']
    vg=json.loads((path/'validation_gate.json').read_text()); rg=json.loads((path/'resource_gate.json').read_text())
    fb.require(vg['passed']==pc.validation_passes(val,cfg),'Validation gate mismatch')
    fb.require(not vg['evaluation_encoded_at_gate'] and not vg['evaluation_scored_at_gate'],'Evaluation opened before gate')
    fb.require(rg['passed']==(rg['projected_total_seconds']<=1200),'Resource gate mismatch')
    rows=[]; pairs=[]
    for p in sorted(path.glob('scores_cohort_*.csv.gz')): rows+=read_rows(p)
    for p in sorted(path.glob('differences_cohort_*.csv.gz')): pairs+=read_rows(p)
    index={(int(r['cohort']),int(r['attack_count']),int(r['permutation']),r['ordering']):r for r in rows}
    fb.require(len(index)==len(rows)==summary['mixed_streams_scored'],'Schedule count mismatch')
    pair_index={(int(r['cohort']),int(r['attack_count']),int(r['permutation']),r['a'],r['b']):r for r in pairs}
    fb.require(len(pair_index)==len(pairs)==summary['paired_comparisons']==len(rows),'Pair count mismatch')
    for key,row in index.items():
        cid,count,permutation,name=key; c=cohorts[cid]
        plan=pc.plan_cohort(cid,len(c['B']),len(c['A']),cfg); ri=cfg['attack_counts'].index(count)
        order=pc.orders_for(plan,cid,ri,permutation,cfg)[name]
        fb.require(row['order_sha256']==hashlib.sha256(order.astype('<i8').tobytes()).hexdigest(),'Schedule hash mismatch')
        fb.require(np.array_equal(order[:110],plan['benign_order'][:110]) and order[110]>=256,'Prefix/onset mismatch')
        fb.require(int(np.sum(order>=256))==count and len(set(order))==256,'Membership/count mismatch')
        first=int(row['first_alert']) if row['first_alert'] else None
        early=first is not None and first<=110
        fb.require(bool_value(row['prefix_alarm'])==early and bool_value(row['at_risk_at_onset'])==(not early),'Risk/prefix classification mismatch')
        expected_delay='' if early or first is None else str(first-111)
        fb.require(bool_value(row['has_attack']),'Mixed stream missing attack label')
        fb.require(row['delay']==expected_delay,'Invalid delay or pre-alert delay')
        fb.require(bool_value(row['right_censored'])==(not early and first is None),'Censoring mismatch')
    for key,row in pair_index.items():
        cid,count,permutation,a,b=key; x=index[(cid,count,permutation,a)]; y=index[(cid,count,permutation,b)]
        fb.require(bool_value(row['changed_alert'])==(bool_value(x['any_alert'])!=bool_value(y['any_alert'])),'Paired alert mismatch')
        fb.require(abs(float(row['score_delta_b_minus_a'])-(float(y['score'])-float(x['score'])))<1e-12,'Paired score mismatch')
    completed=summary['status']=='completed_bounded_pilot'
    if completed:
        fb.require(vg['passed'] and rg['passed'] and len(rows)==9900,'Completed study failed gates/counts')
        fb.require(m['evaluation_encoded'] and m['evaluation_scored'] and len(controls)==11,'Incomplete evaluation')
        for cid in range(12,23):
            fb.require(sum(r[0]==cid for r in index)==900,'Missing cohort schedules')
    elif summary['status'] in ('stopped_validation_failure','blocked_resource_projection'):
        fb.require(not m['evaluation_encoded'] and not m['evaluation_scored'],'Evaluation run despite stop')
        fb.require(not (path/'embedding_evaluation.json').exists(),'Evaluation encoded despite stop')
        fb.require(all(key[0]<15 for key in index),'Evaluation scores present after stop')
    else:
        fb.require(summary['status']=='failed_hard_gate' and len(rows)<9900,'Invalid incomplete status')
    trace_count=0
    if full_logs:
        for name,h in m['full_local_trace_hashes'].items():
            fb.require(fb.sha(path/name)==h,'Local full trace hash mismatch')
            triple={}; current=None
            with gzip.open(path/name,'rt',encoding='utf-8') as f:
                for line in f:
                    tr=json.loads(line); trace_count+=1; cid=tr['cohort']
                    fb.require(tr['w_steps']==list(range(102,257)) and len(tr['distances'])==255,'History/warmup violation')
                    fb.require(abs(tr['score']-(1-min(tr['w'])))<1e-14,'Recorded score/min W mismatch')
                    fb.require(np.all(np.diff(tr['thresholds'])>=0),'Adaptive threshold decreased')
                    if tr['key'] in ('benign','benign_control'): continue
                    count,permutation,order_name=tr['key'].split(':'); group=(cid,int(count),int(permutation))
                    row=index[(*group,order_name)]
                    expected=pc.score_row(tr,threshold,110)
                    for field in ('any_alert','prefix_alarm','at_risk_at_onset','post_onset_first_detection','right_censored'):
                        fb.require(bool_value(row[field])==expected[field],f'Trace-derived {field} mismatch')
                    fb.require(abs(float(row['score'])-tr['score'])<1e-14,'Trace/table score mismatch')
                    if current!=group: triple={}; current=group
                    triple[order_name]=tr
                    if len(triple)==3:
                        for a,b in itertools_pairs():
                            x,y=triple[a],triple[b]; pair=pair_index[(*group,a,b)]
                            fb.require(int(pair['growing_symmetric_difference'])==len(set(x['growing'])^set(y['growing'])),'Growth membership difference mismatch')
                            for label,field in [('distances','distance_mae'),('w','w_mae')]:
                                fb.require(abs(float(pair[field])-float(np.mean(np.abs(np.array(x[label])-y[label]))))<1e-12,'Trajectory MAE mismatch')
    fb.require(m['prior_tracked_files_unchanged'],'Runner found historical mutation')
    if full_logs:
        fb.require(trace_count==12+len(controls)+len(rows),'Full trace ledger count mismatch')
    for control_summary in summary['control_summary']:
        rs=[r for r in controls if r['split']==control_summary['split']]
        k=sum(r['any_alert'] for r in rs)
        fb.require(control_summary['cohorts']==len(rs) and control_summary['any_alerts']==k,'Control summary mismatch')
        if rs:
            fb.require(control_summary['fpr']==k/len(rs),'Control FPR mismatch')
    return {'status':'passed','mixed_rows':len(rows),'pair_rows':len(pairs),'control_cohorts':len(controls),
        'calibration_cohorts':12,'schedule_hashes_reconstructed':len(rows),'full_traces_checked':trace_count,
        'encoder_or_detector_reruns':0,'validation_passed':vg['passed'],'resource_passed':rg['passed'],
        'evaluation_scored':m['evaluation_scored']},rows,pairs


def itertools_pairs():
    return [('random','clustered'),('random','interleaved'),('clustered','interleaved')]


def figures(path,output):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    summary=json.loads((path/'summary.json').read_text()); controls=json.loads((path/'controls.json').read_text())
    cal=json.loads((path/'calibration.json').read_text()); threshold=cal['threshold']
    fig,axes=plt.subplots(1,3,figsize=(14,4),constrained_layout=True)
    axes[0].scatter([0]*12,[r['score'] for r in cal['cohorts']],label='Calibration (12)',alpha=.7)
    for x,split,label in [(1,'validation','Validation controls (3)'),(2,pc.EVAL,'Evaluation controls (8)')]:
        values=[r['score'] for r in controls if r['split']==split]
        if values: axes[0].scatter([x]*len(values),values,label=label)
    axes[0].axhline(threshold,color='black',linestyle='--',label='Calibration-only P95')
    axes[0].set(xticks=[0,1,2],xticklabels=['Calibration','Validation','Evaluation'],ylabel='Maximum score')
    axes[0].legend(fontsize=7)
    for row in controls:
        if row['split']!='validation': continue
        tr=json.loads(gzip.decompress((path/f"control_trace_{row['cohort']:02d}.json.gz").read_bytes()))
        axes[1].plot(tr['w_steps'],tr['w'],label=f"Cohort {row['cohort']}")
    axes[1].axhline(1-threshold,color='black',linestyle='--')
    axes[1].axvline(111,color='gray',linestyle=':')
    axes[1].set(xlabel='Query (all control queries are benign)',ylabel='W',title='Validation control trajectories')
    axes[1].legend(fontsize=7)
    outer=[r for r in summary['outer_summary'] if r['split']==pc.EVAL]
    if outer:
        for name in pc.frozen.ORDERS:
            rs=[r for r in outer if r['ordering']==name]
            axes[2].plot([r['attack_count']/256 for r in rs],[r['mean_cohort_any_alert_rate'] for r in rs],marker='o',label=name)
        axes[2].set(xlabel='Attack fraction',ylabel='Mean any-alert rate (includes prefix alarms)',ylim=(-.03,1.03))
        axes[2].legend(fontsize=8)
    else:
        axes[2].text(.5,.5,'Evaluation not run\nFrozen validation/resource gate stopped study',ha='center',va='center',transform=axes[2].transAxes)
        axes[2].set_axis_off()
    fig.suptitle('Phase C bounded exploratory pilot; source cohorts, not permutations, are outer units')
    fig.savefig(output/'phase_c_diagnostics.png',dpi=170); plt.close(fig)
    split=pc.EVAL if outer else 'validation'
    data=[r for r in summary['per_cohort'] if r['split']==split]
    ids=sorted({r['cohort'] for r in data})
    if ids:
        keys=[(count,name) for count in (26,64,128) for name in pc.frozen.ORDERS]
        lookup={(r['cohort'],r['attack_count'],r['ordering']):r for r in data}
        any_rate=np.array([[lookup[(cid,*key)]['any_alert_rate'] for key in keys] for cid in ids])
        post_rate=np.array([[lookup[(cid,*key)]['post_onset_detection_rate'] if lookup[(cid,*key)]['post_onset_detection_rate'] is not None else np.nan for key in keys] for cid in ids])
        fig,axes=plt.subplots(1,2,figsize=(14,max(4,len(ids)*.55)),constrained_layout=True)
        cmap=plt.get_cmap('Blues').copy(); cmap.set_bad('#dddddd')
        labels=[f'{count/256:.1%}\n{name[0].upper()}' for count,name in keys]
        for ax,values,title in zip(axes,[any_rate,post_rate],['Any alert (P = benign-prefix alarm)','First post-onset detection among at-risk schedules']):
            im=ax.imshow(np.ma.masked_invalid(values),vmin=0,vmax=1,cmap=cmap,aspect='auto')
            ax.set(xticks=range(9),xticklabels=labels,yticks=range(len(ids)),yticklabels=[f'Cohort {cid}' for cid in ids],title=title)
            for i,cid in enumerate(ids):
                for j,key in enumerate(keys):
                    r=lookup[(cid,*key)]; value=values[i,j]
                    text='ineligible' if not np.isfinite(value) else f'{value:.0%}'
                    if title.startswith('Any') and r['prefix_alarm_schedules']: text+=' P'
                    ax.text(j,i,text,ha='center',va='center',fontsize=7,color='white' if np.isfinite(value) and value>.6 else 'black')
        fig.colorbar(im,ax=axes,label='Conditional schedule fraction')
        fig.suptitle('Article-disjoint outer cohorts; R=random, C=clustered, I=interleaved; grey=ineligible')
        fig.savefig(output/'cohort_alarm_breakdown.png',dpi=170); plt.close(fig)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('results',type=Path)
    parser.add_argument('--summary-only',action='store_true',help='Skip local ignored full logs; verify published tables')
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args(); fb.require(not args.output.exists(),'Refusing to overwrite audit output')
    report,_,_=audit(args.results,not args.summary_only)
    args.output.mkdir(parents=True); fb.write(args.output/'verification.json',report)
    figures(args.results,args.output)
    fb.write(args.output/'provenance.json',{'source_sha256':fb.sha(__file__),'input_manifest_sha256':fb.sha(args.results/'artifact_hashes.json'),
                                         'encoder_runs':0,'detector_runs':0})
    fb.write(args.output/'artifact_hashes.json',{p.name:fb.sha(p) for p in args.output.iterdir() if p.is_file()})
    print(json.dumps(report,indent=2))
