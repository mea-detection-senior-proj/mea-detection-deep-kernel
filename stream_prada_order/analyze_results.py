"""Supplemental summaries distinguish benign-prefix alarms from attack detection."""
import argparse
import hashlib
import itertools
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

import experiment as exp
from validate_results import table, flag


def main(path):
    summary = json.loads((path / 'summary.json').read_text())
    rows = table(path / 'stream_scores.csv')
    paired = table(path / 'paired_differences.csv')
    calibration = json.loads((path / 'calibration.json').read_text())
    output = {'any_order_alert_change': [], 'paired_alert_rate_difference': [],
              'first_alert_steps': [], 'calibration_strict_exceedances': sum(x>summary['threshold'] for x in calibration['scores']),
              'calibration_streams': len(calibration['scores'])}
    for ratio in sorted({float(r['attack_ratio']) for r in rows}):
        subset = [r for r in rows if float(r['attack_ratio']) == ratio]
        index = {(int(r['permutation']), r['ordering']): r for r in subset}
        n = len(subset)//3
        changed = sum(len({flag(index[(i,name)]['alert']) for name in exp.ORDERS})>1 for i in range(n))
        output['any_order_alert_change'].append({'attack_ratio':ratio,'changed_triplets':changed,'triplets':n,
            'percent':100*changed/n,'wilson95_conditional':exp.wilson(changed,n)})
        for a,b in itertools.combinations(exp.ORDERS,2):
            delta = np.array([int(flag(index[(i,b)]['alert']))-int(flag(index[(i,a)]['alert'])) for i in range(n)])
            se = float(delta.std(ddof=1)/np.sqrt(n))
            ds=[r for r in paired if float(r['attack_ratio'])==ratio and r['a']==a and r['b']==b]
            output['paired_alert_rate_difference'].append({'attack_ratio':ratio,'a':a,'b':b,
                'a_only_alerts':int(np.sum(delta==-1)),'b_only_alerts':int(np.sum(delta==1)),
                'rate_delta_b_minus_a':float(delta.mean()),
                'normal95_conditional_mean_difference':None if se == 0 else [float(delta.mean()-1.959963984540054*se),float(delta.mean()+1.959963984540054*se)],
                'absolute_difference_upper95_from_disagreement_wilson':exp.wilson(int(np.sum(delta != 0)),n)[1],
                'distance_mae_range':[min(float(r['distance_mae']) for r in ds),max(float(r['distance_mae']) for r in ds)]})
        for name in exp.ORDERS:
            rs=[r for r in subset if r['ordering']==name]
            output['first_alert_steps'].append({'attack_ratio':ratio,'ordering':name,
                'observed_steps':sorted({int(r['first_alert']) for r in rs if r['first_alert']}),
                'prefix_false_alarms':sum(flag(r['prefix_false_alarm']) for r in rs)})
    runtimes=np.array([float(r['runtime_seconds']) for r in rows])
    output['stream_runtime_seconds']={'mean':float(runtimes.mean()),'p95':float(np.quantile(runtimes,.95)),
                                      'max':float(runtimes.max()),'sum':float(runtimes.sum())}
    output['interpretation']='Conditional offline permutation evidence only; any alert includes prefix false positives. Rate-difference intervals are normal intervals for paired Monte Carlo means.'
    exp.json_write(path/'supplemental_summary.json',output)
    groups=summary['detection']
    labels=[f"{g['attack_ratio']:.1%} {g['ordering']}" for g in groups]
    prefix=np.array([g['prefix_false_alarms']/g['streams'] for g in groups])
    post=np.array([g['detected_nonprefix']/g['streams'] for g in groups])
    missed=np.array([g['right_censored']/g['streams'] for g in groups])
    fig,axes=plt.subplots(1,2,figsize=(13,5),constrained_layout=True,gridspec_kw={'width_ratios':[2.2,1]})
    y=np.arange(len(groups))
    axes[0].barh(y,post,label='First alarm at/after attack onset',color='#377eb8')
    axes[0].barh(y,prefix,left=post,label='Benign-prefix false alarm',color='#e68632')
    axes[0].barh(y,missed,left=post+prefix,label='No alarm by stream end',color='#cccccc')
    axes[0].set(yticks=y,yticklabels=labels,xlabel='Fraction of 1,000 schedules',xlim=(0,1))
    axes[0].invert_yaxis()
    handles, legend_labels=axes[0].get_legend_handles_labels()
    fig.legend(handles,legend_labels,loc='outside lower center',ncol=3,fontsize=9)
    fpr=summary['held_out_benign']; lo,hi=fpr['wilson95_conditional']
    axes[1].errorbar([0],[fpr['fpr']],yerr=[[fpr['fpr']-lo],[hi-fpr['fpr']]],fmt='o',capsize=6,label=f"Held-out ({fpr['alerts']}/{fpr['streams']})")
    axes[1].axhline(.05,color='red',linestyle='--',label='Nominal 5% target')
    axes[1].set(xticks=[0],xticklabels=['Benign streams'],ylabel='Stream-level false positive rate',ylim=(0,.3))
    axes[1].legend(fontsize=8)
    fig.suptitle('First-alarm outcomes and conditional benign FPR; simulated offline schedules')
    fig.savefig(path/'alarm_outcomes.png',dpi=170)
    plt.close(fig)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('results',type=Path)
    main(parser.parse_args().results)
