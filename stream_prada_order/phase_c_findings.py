"""Descriptive evaluation summaries from audited Phase C tables, without reruns."""
import argparse
import itertools
import json
from pathlib import Path

import numpy as np

import phase_c_audit as audit
import phase_c_runner as pc
import phase_b_feasibility as fb


def main(results,output):
    fb.require(not output.exists(),'Refusing to overwrite findings')
    rows=[]; pairs=[]
    for p in results.glob('scores_cohort_*.csv.gz'): rows+=audit.read_rows(p)
    for p in results.glob('differences_cohort_*.csv.gz'): pairs+=audit.read_rows(p)
    rows=[r for r in rows if r['split']==pc.EVAL]
    pairs=[r for r in pairs if r['split']==pc.EVAL]
    ids=sorted({int(r['cohort']) for r in rows})
    summary=json.loads((results/'summary.json').read_text())
    index={(int(r['cohort']),int(r['attack_count']),int(r['permutation']),r['ordering']):r for r in rows}
    findings={'outer_cohorts':len(ids),'evaluation_streams':len(rows),'detection':[],'paired':[],'changed_triplets':[]}
    for count in (26,64,128):
        for name in pc.frozen.ORDERS:
            rs=[r for r in rows if int(r['attack_count'])==count and r['ordering']==name]
            if not rs: continue
            detected=sum(audit.bool_value(r['post_onset_first_detection']) for r in rs)
            eligible=sum(audit.bool_value(r['at_risk_at_onset']) for r in rs)
            delays=[int(r['delay']) for r in rs if r['delay']]
            any_rate=sum(audit.bool_value(r['any_alert']) for r in rs)/len(rs)
            existing=next(r for r in summary['outer_summary'] if r['split']==pc.EVAL and r['attack_count']==count and r['ordering']==name)
            fb.require(abs(any_rate-existing['mean_cohort_any_alert_rate'])<1e-12,'Outer rate audit mismatch')
            findings['detection'].append({'attack_count':count,'ordering':name,'outer_cohorts':len(ids),'schedules':len(rs),
                'any_alerts':sum(audit.bool_value(r['any_alert']) for r in rs),'prefix_alarms':sum(audit.bool_value(r['prefix_alarm']) for r in rs),
                'eligible_schedules':eligible,'post_onset_detections':detected,'post_onset_rate':detected/eligible if eligible else None,
                'median_detected_delay':float(np.median(delays)) if delays else None,'detected_delay_n':len(delays),
                'right_censored':sum(audit.bool_value(r['right_censored']) for r in rs),
                'mean_max_score':float(np.mean([float(r['score']) for r in rs]))})
        if not ids: continue
        permutations=sorted({int(r['permutation']) for r in rows if int(r['attack_count'])==count})
        changed=sum(len({audit.bool_value(index[(cid,count,p,name)]['any_alert']) for name in pc.frozen.ORDERS})>1
                    for cid in ids for p in permutations)
        findings['changed_triplets'].append({'attack_count':count,'changed':changed,'triplets':len(ids)*len(permutations),
                                              'fraction':changed/(len(ids)*len(permutations))})
        for a,b in itertools.combinations(pc.frozen.ORDERS,2):
            ds=[r for r in pairs if int(r['attack_count'])==count and r['a']==a and r['b']==b]
            per_cohort=[np.mean([audit.bool_value(r['changed_alert']) for r in ds if int(r['cohort'])==cid]) for cid in ids]
            delta=[float(int(audit.bool_value(index[(cid,count,p,b)]['any_alert']))-int(audit.bool_value(index[(cid,count,p,a)]['any_alert'])))
                   for cid in ids for p in permutations]
            findings['paired'].append({'attack_count':count,'a':a,'b':b,'changed_alerts':sum(audit.bool_value(r['changed_alert']) for r in ds),
                'pairs':len(ds),'mean_cohort_changed_fraction':float(np.mean(per_cohort)),
                'cohort_changed_fraction_range':[float(min(per_cohort)),float(max(per_cohort))],
                'mean_paired_rate_difference_b_minus_a':float(np.mean(delta)),
                **{'mean_'+field:float(np.mean([float(r[field]) for r in ds])) for field in
                   ('score_delta_b_minus_a','growing_symmetric_difference','distance_mae','w_mae')}})
    findings['caveat']='Descriptive conditional schedules on 8 reused-article cohorts, not 800 independent population trials; delays condition on detections.'
    findings['source_sha256']=fb.sha(__file__)
    findings['input_manifest_sha256']=fb.sha(results/'artifact_hashes.json')
    fb.write(output,findings)
    print(json.dumps(findings,indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('results',type=Path); parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args(); main(args.results,args.output)
