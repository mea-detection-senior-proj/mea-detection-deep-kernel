"""Scientific diagnostics; fixed example schedules, no result-driven selection."""
import numpy as np


def plots(out,records,features,growth,fit,cfg,summary,assoc):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import phase_e_analysis as e
    fig,axes=plt.subplots(1,3,figsize=(15,4.5),layout='constrained')
    for cid in [12,13,14]:
        f=features[str(cid)]
        for x,label in [(0,'B'),(1,'A')]:
            values=[r['words'] for r in f[label]]
            axes[0].scatter(np.full(len(values),x+(cid-13)*.15),values,s=7,alpha=.2)
    axes[0].axhspan(np.expm1(fit['length']['support'][0]),np.expm1(fit['length']['support'][1]),alpha=.15,color='green',label='Fit benign support')
    axes[0].set(xticks=[0,1],xticklabels=['Benign','Attack'],ylabel='Whitespace word count (log scale)',yscale='log',title='Unique query reservoirs; 3 source cohorts')
    axes[0].legend(fontsize=7)
    names=['original','length_endpoint','distance_mean_endpoint','cusum_k0.5','cusum_k1.0','length_adjusted_k0.5','prefix_centered_k0.5','combined_k0.5']
    for i,name in enumerate(names):
        ctrl=next(c for c in summary['controls'] if c['candidate']==name and c['alpha']==.2)
        cs=[c for c in summary['cells'] if c['candidate']==name and c['alpha']==.2 and c['attack_count']==64]
        rates=[np.mean([p['tpr_all_schedules'] for c in cs for p in c['per_cohort'] if p['cohort']==cid]) for cid in [12,13,14]]
        axes[1].scatter([i]*3,rates,s=20)
        axes[1].plot([i-.2,i+.2],[np.mean(rates)]*2,color='black')
        axes[1].text(i,1.04,f'FP {ctrl["false_alarms"]}/3',ha='center',fontsize=7,rotation=45)
    axes[1].set(xticks=range(len(names)),xticklabels=names,ylim=(-.03,1.2),ylabel='Mean detection rate over 3 orders',title='25% attack, alpha=.20; each dot is one cohort')
    axes[1].tick_params(axis='x',rotation=80)
    for k in [.5,1.]:
        for name in ['cusum','length_adjusted','prefix_centered','combined']:
            cs=[c for c in summary['cells'] if c['candidate']==f'{name}_k{k}' and c['alpha']==.2 and c['attack_count']==128]
            axes[2].plot(range(3),[c['tpr_all_schedules'] for c in cs],marker='o',label=f'{name} k={k}')
    axes[2].set(xticks=range(3),xticklabels=['R','C','I'],ylabel='Post-onset detections / all schedules',ylim=(-.03,1.03),title='50% attack: length/source controls')
    axes[2].legend(fontsize=6)
    fig.suptitle('Phase E development diagnostics: length/format overlap and FPR must accompany TPR')
    fig.savefig(out/'shortcut_controls.png',dpi=140); plt.close(fig)
    fig,axes=plt.subplots(4,3,figsize=(14,9),layout='constrained')
    for col,cid in enumerate([12,13,14]):
        r=next(r for r in records if r['cohort']==cid and r['key']=='64:0:random')
        f=e.feature_arrays(r,features); g=growth[f'{cid}|{r["key"]}']; stats=e.curves(r,features,fit,cfg)
        axes[0,col].plot(range(1,257),f['words']); axes[0,col].set(title=f'Cohort {cid}: {features[str(cid)]["article"][:32]}',ylabel='Words')
        axes[1,col].plot(range(2,257),r['distances']); axes[1,col].set(ylabel='Minimum distance')
        axes[2,col].plot(range(1,257),g['counts']); axes[2,col].set(ylabel='Growing Set size')
        for name in ['cusum_k0.5','length_adjusted_k0.5','prefix_centered_k0.5','combined_k0.5']:
            axes[3,col].plot(*stats[name],label=name)
        axes[3,col].set(ylabel='CUSUM statistic (own calibrated scales)',xlabel='Query')
        for row in range(4): axes[row,col].axvline(111,color='gray',linestyle=':')
    axes[3,2].legend(fontsize=6)
    fig.suptitle('Fixed examples: 25% attack, random ordering, permutation 0; no example selection by outcome')
    fig.savefig(out/'length_distance_growth_paths.png',dpi=140); plt.close(fig)
