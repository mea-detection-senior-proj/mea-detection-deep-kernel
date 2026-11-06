"""Additional Phase A diagnostics from saved traces only; no model/detector run."""
import argparse
import csv
import gzip
import hashlib
import json
from pathlib import Path

import numpy as np
from scipy.stats import skew, kurtosis, spearmanr

import failure_analysis as fa
import experiment as frozen


def distance_details(values):
    raw=np.asarray(values,dtype=float)
    filtered=frozen.base.trim_outliers_3sigma(raw)
    variable=len(filtered)>=4 and float(filtered.std())>1e-12
    return {'raw_samples':len(raw),'kept_samples':len(filtered),'removed_samples':len(raw)-len(filtered),
            'raw_mean':float(raw.mean()),'raw_std':float(raw.std()),
            'filtered_mean':float(filtered.mean()),'filtered_std':float(filtered.std()),
            'filtered_skew':float(skew(filtered,bias=False)) if variable else None,
            'filtered_excess_kurtosis':float(kurtosis(filtered,bias=False)) if variable else None}


def trace_details(trace, threshold):
    first=fa.first_crossing(trace,threshold)
    final_below=trace['w'][-1]<1-threshold
    count=None if first is None else trace['kept_shapiro_samples'][trace['w_steps'].index(first)]
    return {'stream':trace['stream'],'score':trace['score'],'first_alert':first,
            'minimum_w_step':trace['w_steps'][int(np.argmin(trace['w']))],
            'first_w':trace['w'][0],'final_w':trace['w'][-1],
            'final_w_below_threshold':final_below,'final_w_recovered':first is not None and not final_below,
            'kept_at_first_alert':count,
            'early_distance_mean':float(np.mean(trace['distances'][:101])),
            'late_distance_mean':float(np.mean(trace['distances'][101:])),
            **{'q102_'+k:v for k,v in distance_details(trace['distances'][:101]).items()}}


def main(args):
    fa.require(not args.output.exists(),'Refusing to overwrite diagnostics')
    args.output.mkdir(parents=True)
    manifest=json.loads((args.phase_a/'artifact_hashes.json').read_text())
    for name,h in manifest.items():
        fa.require(fa.sha(args.phase_a/name)==h,f'Phase A evidence mismatch: {name}')
    analysis=json.loads((args.phase_a/'analysis.json').read_text())
    threshold=analysis['threshold']
    summaries={}; rows=[]
    for key in ('calibration','benign'):
        traces=json.loads(gzip.decompress((args.phase_a/f'{key}_replay_traces.json.gz').read_bytes()))
        rs=[{'pool':key,**trace_details(tr,threshold)} for tr in traces]
        rows.extend(rs)
        alerts=[r for r in rs if r['first_alert'] is not None]
        summaries[key]={'streams':len(rs),'ever_alerts':len(alerts),
            'final_w_below_threshold':sum(r['final_w_below_threshold'] for r in rs),
            'alerted_then_recovered_by_end':sum(r['final_w_recovered'] for r in rs),
            'minimum_w_at_first_test':sum(r['minimum_w_step']==102 for r in rs),
            'mean_early_distance':float(np.mean([r['early_distance_mean'] for r in rs])),
            'mean_late_distance':float(np.mean([r['late_distance_mean'] for r in rs])),
            'kept_at_first_alert_range':[min(r['kept_at_first_alert'] for r in alerts),max(r['kept_at_first_alert'] for r in alerts)]}
    fa.write_csv(args.output/'per_stream_details.csv',rows)
    source_rows=list(csv.DictReader((args.phase_a/'stream_source_features.csv').open(encoding='utf-8')))
    correlations={}
    for pool in ('calibration','benign'):
        rs=[r for r in source_rows if r['pool']==pool]
        correlations[pool]={key:float(spearmanr([float(r[key]) for r in rs],[float(r['score']) for r in rs]).statistic)
                             for key in ('source_groups','effective_groups_hhi','largest_group_fraction','mean_words')}
    examples=json.loads((args.results/'example_traces.json').read_text())
    prefixes={ratio:distance_details(traces['random']['distances'][:101]) for ratio,traces in examples.items()}
    output={'by_pool':summaries,'prefix_distances_at_first_test':prefixes,
            'descriptive_score_feature_spearman':correlations,
            'caveats':['Recovery at final W does not cancel a previous stream alert.',
                       'Distance summaries and feature correlations are descriptive, not causal explanations.',
                       'No alternative threshold or revised detector is evaluated.']}
    fa.write_json(args.output/'details.json',output)
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(1,2,figsize=(10,4),constrained_layout=True)
    false=[r for r in rows if r['pool']=='benign' and r['first_alert'] is not None]
    axes[0].hist([r['first_alert'] for r in false],bins=[101.5,110.5,128.5,160.5,192.5,224.5,256.5],edgecolor='white')
    axes[0].set(xlabel='First false-positive query',ylabel='Streams',title='34 held-out benign false positives')
    axes[1].scatter([r['first_w'] for r in false],[r['final_w'] for r in false],s=24)
    axes[1].axhline(1-threshold,color='black',linestyle='--'); axes[1].axvline(1-threshold,color='black',linestyle='--')
    axes[1].set(xlabel='W at first eligible test (query 102)',ylabel='W at stream end (query 256)',title='29/34 have recovered W at the endpoint')
    fig.savefig(args.output/'false_positive_recovery.png',dpi=170); plt.close(fig)
    fa.write_json(args.output/'provenance.json',{'source_sha256':fa.sha(__file__),'phase_a_source_sha256':fa.sha(fa.__file__),
        'input_manifest_sha256':fa.sha(args.phase_a/'artifact_hashes.json'),'model_runs':0,'detector_runs':0,
        'original_example_traces_sha256':fa.sha(args.results/'example_traces.json')})
    fa.write_json(args.output/'artifact_hashes.json',{p.name:fa.sha(p) for p in sorted(args.output.iterdir()) if p.is_file()})
    print(json.dumps(output,indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--phase-a',type=Path,default=fa.ROOT/'stream_prada_order/diagnostics/phase_a')
    parser.add_argument('--results',type=Path,default=fa.ROOT/'stream_prada_order/results/seed20261106_25min_retry1')
    parser.add_argument('--output',type=Path,required=True)
    main(parser.parse_args())
