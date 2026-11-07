"""Construct proposed split certificates and figures, without scoring any query."""
import argparse
import gzip
import json
from pathlib import Path

import phase_b_feasibility as fb


def main(args):
    fb.require(not args.output.exists(),'Refusing to overwrite proposed plans')
    args.output.mkdir(parents=True)
    groups=json.loads(gzip.decompress((args.audit/'source_groups.json.gz').read_bytes()))
    proposals=[('article','model_leeching',12,3,8),('passage','model_leeching',20,4,14),
               ('passage','ME_BERT_boolq_wiki',20,4,10)]
    summaries=[]
    for mode,ds,ncal,nval,ntest in proposals:
        active=[{'id':g['id'],**g['by_dataset'][ds]} for g in groups[mode]
                if any(g['by_dataset'][ds].values()) and (mode!='article' or g['known_article'])]
        cohorts,_=fb.allocate(active,[(256,0)]*ncal+[(256,128)]*(nval+ntest))
        fb.require(len(cohorts)==ncal+nval+ntest,'Proposed allocation is not feasible')
        for i,c in enumerate(cohorts):
            c['split']='calibration' if i<ncal else ('validation' if i<ncal+nval else 'final_test_partition_not_fresh_confirmation')
        name=f'proposed_{mode}_{ds}_{ncal}_{nval}_{ntest}.json.gz'
        fb.save_cohorts(args.output/name,cohorts)
        summaries.append({'dataset':ds,'grouping':mode,'calibration':ncal,'validation':nval,'final_partition':ntest,
                          'certificate':name,'zero_fp_one_sided_95_upper':fb.zero_fp_upper(ntest),
                          'untouched_final_test':False,'executed':False})
    fb.write(args.output/'proposed_allocations.json',summaries)
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(1,2,figsize=(11,4),constrained_layout=True)
    labels=['Model / passage','Model / article','BoolQ / passage','BoolQ / mapped article']
    axes[0].barh(labels,[38,23,36,0],label='Benign 256')
    axes[0].set(xlabel='Certified constructed cohorts under stated grouping',title='Alternative capacities; not additive')
    axes[0].invert_yaxis()
    ns=list(range(2,301))
    axes[1].plot(ns,[fb.zero_fp_upper(n) for n in ns])
    axes[1].axhline(.05,color='red',linestyle='--',label='5% FPR')
    for n in (8,10,14,59): axes[1].plot(n,fb.zero_fp_upper(n),'o')
    axes[1].set(xlabel='Independent Bernoulli cohorts (assumption)',ylabel='One-sided 95% upper FPR if zero FP',ylim=(0,.5))
    axes[1].legend(fontsize=8)
    fig.savefig(args.output/'capacity_uncertainty.png',dpi=170); plt.close(fig)
    fb.write(args.output/'provenance.json',{'source_sha256':fb.sha(__file__),
        'input_groups_sha256':fb.sha(args.audit/'source_groups.json.gz'),'encoder_runs':0,'detector_runs':0,
        'note':'These are feasibility certificates, not detector results or final experiment configurations.'})
    fb.write(args.output/'artifact_hashes.json',{p.name:fb.sha(p) for p in sorted(args.output.iterdir()) if p.is_file()})
    print(json.dumps(summaries,indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--audit',type=Path,default=fb.ROOT/'stream_prada_order/diagnostics/phase_b_verified')
    parser.add_argument('--output',type=Path,required=True)
    main(parser.parse_args())
