"""Phase A evidence audit and optional exact benign replay; no detector changes.

Saved-result analysis is the default. --replay invokes the unchanged frozen
encoder and experiment.trace only to recover omitted benign timing/trajectories.
No thresholds are fitted on test data. All outputs go to a new directory.
"""
from __future__ import annotations

import argparse
from collections import Counter
import csv
import gzip
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import time

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
HORIZONS = (101, 102, 110, 128, 160, 192, 224, 256)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False),
                          encoding='utf-8', newline='\n')


def write_csv(path, rows):
    with Path(path).open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)


def table(path):
    path = Path(path)
    data = gzip.decompress(path.with_suffix(path.suffix+'.gz').read_bytes())
    return list(csv.DictReader(io.StringIO(data.decode('utf-8'))))


def first_crossing(trace, threshold, horizon=None):
    return next((int(step) for step,w in zip(trace['w_steps'],trace['w'])
                 if (horizon is None or step <= horizon) and w < 1-threshold), None)


def horizon_score(trace, horizon):
    return float(1-min([1.0]+[w for step,w in zip(trace['w_steps'],trace['w']) if step<=horizon]))


def check_replay(saved_score, saved_alert, trace, threshold):
    require(abs(float(saved_score)-trace['score']) <= 1e-10, 'Replayed score differs from frozen result')
    require(bool(saved_alert)==(first_crossing(trace,threshold) is not None), 'Replayed alert differs')


def timing_inventory(rows):
    available = all('first_alert' in r for r in rows)
    return {'first_alert_saved':available,'first_alert_steps':
            [r['first_alert'] for r in rows] if available else None,
            'reason':None if available else 'Original benign CSV stores stream, score and alert only.'}


def connected_components(keys):
    parent = list(range(len(keys)))
    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]; i = parent[i]
        return i
    seen = {}
    for i, row in enumerate(keys):
        for key in row:
            if key in seen:
                a,b = find(i),find(seen[key])
                if a!=b:
                    parent[b]=a
            else:
                seen[key]=i
    return [find(i) for i in range(len(keys))]


def composition(groups):
    counts = np.array(list(Counter(groups).values()),dtype=float)
    require(len(counts)>0,'Empty group composition')
    p=counts/counts.sum()
    return {'queries':len(groups),'source_groups':len(counts),
            'largest_group_fraction':float(p.max()),'effective_groups_hhi':float(1/np.sum(p*p)),
            'groups_with_multiple_queries':int(np.sum(counts>1))}


def score_distribution(scores, threshold):
    scores=np.asarray(scores,dtype=float)
    return {'streams':len(scores),'mean':float(scores.mean()),'std':float(scores.std()),
            'quantiles':dict(zip(('min','p05','p25','median','p75','p95','max'),
                                np.quantile(scores,[0,.05,.25,.5,.75,.95,1]).tolist())),
            'exceedances':int(np.sum(scores>threshold)), 'threshold':threshold}


def restore_data(metadata, data_root):
    sys.path.insert(0,str(ROOT/'pilot'))
    import protocol
    cfg=metadata['config']
    paths=[data_root/label/'queries.jsonl' for label in ('normal','attacker')]
    require([sha(p) for p in paths]==[cfg['normal_sha256'],cfg['attacker_sha256']], 'Raw data hash drift')
    normal,attack=[protocol.read_rows(p) for p in paths]
    partitions,audit=protocol.make_partitions(normal,attack,cfg['seed'])
    require(audit==metadata['split_audit'],'Split reconstruction mismatch')
    all_rows=normal+attack
    keys=[]
    for i,row in enumerate(all_rows):
        rowkeys=[('id',row['id']),('text',protocol.normalize(row['query']))]
        if i>=len(normal):
            context=protocol.context_of(row['query'])
            require(context is not None,'Unparsed attack context')
            rowkeys.append(('context',context))
        keys.append(rowkeys)
    components=connected_components(keys)
    group_ids={}
    for row,g in zip(all_rows,components):
        group_ids.setdefault(g,set()).add(row['id'])
    group_hash={g:hashlib.sha256('\0'.join(sorted(ids)).encode()).hexdigest() for g,ids in group_ids.items()}
    query_group={hashlib.sha256(protocol.normalize(row['query']).encode()).hexdigest():group_hash[g]
                 for row,g in zip(all_rows,components)}
    pools={}; rng=np.random.default_rng(cfg['seed']+1)
    for key,part,label in [('calibration','calibration','benign'),('benign','test','benign'),('attack','test','attack')]:
        source=partitions[part][label]
        selected=[source[i] for i in rng.permutation(len(source))[:cfg['pool_limit']]]
        hashes=[hashlib.sha256(protocol.normalize(r['query']).encode()).hexdigest() for r in selected]
        require(hashes==metadata['pool_query_sha256'][key],f'Pool mismatch: {key}')
        pools[key]={'rows':selected,'groups':[query_group[h] for h in hashes],
                    'words':[len(r['query'].split()) for r in selected],
                    'characters':[len(r['query']) for r in selected]}
    return pools,query_group


def make_stream_indices(cfg, pools):
    output={}
    for key,offset in [('calibration',2),('benign',3)]:
        rng=np.random.default_rng(cfg['seed']+offset)
        count=cfg['calibration_streams'] if key=='calibration' else cfg['benign_eval_streams']
        output[key]=[rng.choice(len(pools[key]['rows']),cfg['stream_length'],replace=False) for _ in range(count)]
    return output


def stream_features(pool, indices):
    groups=[pool['groups'][i] for i in indices]
    return {**composition(groups),'mean_words':float(np.mean([pool['words'][i] for i in indices])),
            'mean_characters':float(np.mean([pool['characters'][i] for i in indices]))}


def saved_analysis(results, metadata, pools, indices):
    cfg=metadata['config']; threshold=json.loads((results/'calibration.json').read_text())['p95_threshold']
    calibration=json.loads((results/'calibration.json').read_text())['scores']
    benign=table(results/'benign_scores.csv'); mixed=table(results/'stream_scores.csv')
    examples=json.loads((results/'example_traces.json').read_text())
    source={k:{**composition(v['groups']),'mean_words':float(np.mean(v['words'])),
                  'median_words':float(np.median(v['words'])),'word_p95':float(np.quantile(v['words'],.95))}
            for k,v in pools.items()}
    source['calibration_test_group_overlap']=len(set(pools['calibration']['groups'])&set(pools['benign']['groups']))
    source['calibration_test_query_overlap']=len(set(metadata['pool_query_sha256']['calibration'])&set(metadata['pool_query_sha256']['benign']))
    stream_rows=[]
    for key,scores in [('calibration',calibration),('benign',[float(r['score']) for r in benign])]:
        for i,(ids,score) in enumerate(zip(indices[key],scores)):
            stream_rows.append({'pool':key,'stream':i,'score':score,'alert':float(score)>threshold,
                                **stream_features(pools[key],ids)})
    # Exact within-stream grouping is reconstructed; labels are from frozen scores.
    comparisons={}
    for label,rs in [('calibration',[r for r in stream_rows if r['pool']=='calibration']),
                     ('test_fp',[r for r in stream_rows if r['pool']=='benign' and r['alert']]),
                     ('test_tn',[r for r in stream_rows if r['pool']=='benign' and not r['alert']])]:
        comparisons[label]={'streams':len(rs),**{k:float(np.mean([r[k] for r in rs])) for k in
            ('source_groups','effective_groups_hhi','largest_group_fraction','mean_words','mean_characters')}}
    prefixes=[]; prefix_ids={}
    for ri,ratio in enumerate(cfg['attack_ratios']):
        rng=np.random.default_rng(cfg['seed']+100+ri)
        count=round(cfg['stream_length']*ratio)
        ids=rng.permutation(len(pools['benign']['rows']))[:cfg['stream_length']-count][:cfg['benign_prefix']]
        prefix_ids[ratio]=ids
        traces=examples[str(ratio)]
        for tr in traces.values():
            require(np.array_equal(tr['query_indices'][:cfg['benign_prefix']],ids),'Saved prefix mismatch')
        first=traces['random']
        prefix_w=[w for s,w in zip(first['w_steps'],first['w']) if s<=cfg['benign_prefix']]
        for tr in traces.values():
            require(prefix_w==[w for s,w in zip(tr['w_steps'],tr['w']) if s<=cfg['benign_prefix']], 'Nonidentical paired prefix trajectory')
        subset=[r for r in mixed if float(r['requested_ratio'])==ratio]
        prefixes.append({'requested_ratio':ratio,'prefix_query_indices':ids.tolist(),
            'query_hash_sequence_sha256':hashlib.sha256('\0'.join(metadata['pool_query_sha256']['benign'][i] for i in ids).encode()).hexdigest(),
            **stream_features(pools['benign'],ids),'w_at_102':prefix_w[0],
            'minimum_prefix_w':min(prefix_w),'prefix_first_alert':first_crossing(first,threshold,cfg['benign_prefix']),
            'prefix_alert_rows':sum(r['prefix_false_alarm']=='True' for r in subset),'mixed_rows':len(subset)})
    overlaps=[]
    for i,a in enumerate(cfg['attack_ratios']):
        for b in cfg['attack_ratios'][i+1:]:
            x,y=prefix_ids[a],prefix_ids[b]
            overlaps.append({'a':a,'b':b,'shared_query_members':len(set(x)&set(y)),
                             'identical_position_queries':int(np.sum(x==y)),
                             'shared_source_groups':len(set(pools['benign']['groups'][i] for i in x)&set(pools['benign']['groups'][i] for i in y))})
    # Reuse is quantified at query membership level; no independence claim.
    reuse={}
    for key,streams in indices.items():
        sets=[set(s) for s in streams]
        overlaps_query=[len(sets[i]&sets[j]) for i in range(len(sets)) for j in range(i+1,len(sets))]
        reuse[key]={'streams':len(streams),'distinct_queries_used':len(set().union(*sets)),
                    'mean_pairwise_shared_queries':float(np.mean(overlaps_query)),
                    'sampling':'same fixed pool; without replacement within stream, reused across streams'}
    return {'threshold':threshold,'timing_inventory':timing_inventory(benign),
            'calibration_distribution':score_distribution(calibration,threshold),
            'test_distribution':score_distribution([float(r['score']) for r in benign],threshold),
            'source_composition':source,'stream_feature_comparisons':comparisons,
            'stream_construction':reuse,'prefixes':prefixes,'prefix_overlaps':overlaps},stream_rows


def replay_benign(results, metadata, pools, indices, output, model_root, max_seconds=120):
    """Recover omitted traces by calling the frozen original encoder/detector."""
    started=time.perf_counter()
    import psutil
    import torch
    import sentence_transformers
    from sentence_transformers import SentenceTransformer
    import experiment as frozen
    cfg=metadata['config']; torch.set_num_threads(1)
    for name,h in metadata['source_files_sha256'].items():
        require(sha(ROOT/name)==h,f'Frozen source drift: {name}')
    model_path=model_root/cfg['model_revision']
    for name,h in metadata['model_files_sha256'].items():
        require(sha(model_path/name)==h,f'Model file drift: {name}')
    require(torch.cuda.is_available(),'CUDA unavailable; no fallback replay')
    free_gpu,_=torch.cuda.mem_get_info()
    require(free_gpu>=int(1.5*1024**3),'Replay requires 1.5 GiB free driver GPU memory')
    require(psutil.virtual_memory().available>=2*1024**3,'Replay requires 2 GiB free RAM')
    torch.cuda.reset_peak_memory_stats()
    model=SentenceTransformer(str(model_path),device='cuda',local_files_only=True)
    model.eval()
    for p in model.parameters():
        p.requires_grad_(False)
    require(model.max_seq_length==cfg['max_seq_length'],'Encoder sequence length drift')
    all_rows=sum([pools[k]['rows'] for k in ('calibration','benign','attack')],[])
    with torch.inference_mode():
        embeddings=model.encode([r['query'] for r in all_rows],batch_size=cfg['embedding_batch_size'],
                                normalize_embeddings=True,convert_to_numpy=True,show_progress_bar=True)
    embedding_hash=hashlib.sha256(embeddings.tobytes()).hexdigest()
    require(embedding_hash==metadata['embedding_sha256'],'Embedding replay hash is not identical')
    ncal=len(pools['calibration']['rows'])
    tensors=[torch.from_numpy(embeddings[:ncal]),torch.from_numpy(embeddings[ncal:])]
    matrices=[torch.cdist(z,z).numpy() for z in tensors]
    saved={'calibration':json.loads((results/'calibration.json').read_text())['scores'],
           'benign':[float(r['score']) for r in table(results/'benign_scores.csv')]}
    threshold=json.loads((results/'calibration.json').read_text())['p95_threshold']
    traces={}; timing_rows=[]; maximum_error=0.0
    for key,matrix in zip(('calibration','benign'),matrices):
        records=[]
        for i,order in enumerate(indices[key]):
            require(time.perf_counter()-started<max_seconds,'Replay exceeded announced 120-second budget')
            tr=frozen.trace(matrix,order)
            check_replay(saved[key][i],saved[key][i]>threshold,tr,threshold)
            maximum_error=max(maximum_error,abs(tr['score']-saved[key][i]))
            # Reapply only the frozen outlier filter to recorded distances.
            # This does not rerun Shapiro or introduce another scoring rule.
            kept=[len(frozen.base.trim_outliers_3sigma(np.asarray(tr['distances'][:step-1],dtype=np.float64)))
                  for step in tr['w_steps']]
            compact={'stream':i,'query_indices':order.tolist(),'distances':tr['distances'],
                     'w_steps':tr['w_steps'],'w':tr['w'],'kept_shapiro_samples':kept,
                     'score':tr['score'],'growing':tr['growing']}
            records.append(compact)
            first=first_crossing(tr,threshold)
            kept_at_first=None if first is None else kept[tr['w_steps'].index(first)]
            timing_rows.append({'pool':key,'stream':i,'score':tr['score'],'alert':first is not None,
                'first_alert':first,'raw_distances_at_first':None if first is None else first-1,
                'kept_samples_at_first':kept_at_first,
                'first_w':tr['w'][0],'min_w':min(tr['w']),
                'removed_at_first':None if first is None else first-1-kept_at_first})
        traces[key]=records
        data=json.dumps(records,separators=(',',':'),allow_nan=False).encode()
        (output/f'{key}_replay_traces.json.gz').write_bytes(gzip.compress(data,mtime=0))
        print(f'Replayed {key}: {len(records)} streams; all frozen scores matched',flush=True)
    provenance={'status':'completed','encoder_rerun':True,'detector_streams_replayed':400,
                'embedding_hash_matches_original':True,'embedding_sha256':embedding_hash,
                'maximum_original_score_abs_error':maximum_error,'threshold_unchanged':threshold,
                'seconds':time.perf_counter()-started,'announced_budget_seconds':max_seconds,
                'peak_process_working_set_bytes':psutil.Process().memory_info().peak_wset,
                'gpu_peak_allocated_bytes':torch.cuda.max_memory_allocated(),
                'gpu_peak_reserved_bytes':torch.cuda.max_memory_reserved(),
                'torch':torch.__version__,'sentence_transformers':sentence_transformers.__version__,
                'note':'Exact recovery of omitted timing. No new mixed streams, threshold fitting or detector changes.'}
    write_json(output/'replay_provenance.json',provenance)
    write_csv(output/'replay_timing.csv',timing_rows)
    return traces,timing_rows


def analyze_replay(traces, timing_rows, threshold, cfg):
    horizons=[]
    for key,records in traces.items():
        for horizon in HORIZONS:
            scores=[horizon_score(tr,horizon) for tr in records]
            counts=[n for tr in records for step,n in zip(tr['w_steps'],tr['kept_shapiro_samples']) if step==horizon]
            horizons.append({'pool':key,'horizon':horizon,'streams':len(records),
                'cumulative_alerts':sum(first_crossing(tr,threshold,horizon) is not None for tr in records),
                'cumulative_fpr':sum(first_crossing(tr,threshold,horizon) is not None for tr in records)/len(records),
                'available_tests':max(0,horizon-101),'raw_distances':horizon-1,
                'mean_kept_shapiro_samples':float(np.mean(counts)) if counts else None,
                'mean_max_score':float(np.mean(scores)),
                'threshold':threshold})
    false_positives=[r for r in timing_rows if r['pool']=='benign' and r['alert']]
    steps=[r['first_alert'] for r in false_positives]
    bins=[(102,110),(111,128),(129,160),(161,192),(193,224),(225,256)]
    timing={'test_fp_streams':len(false_positives),'first_at_102':sum(x==102 for x in steps),
            'first_by_110':sum(x<=110 for x in steps),
            'median_first_alert':float(np.median(steps)) if steps else None,
            'first_alert_range':[min(steps),max(steps)] if steps else None,
            'bins':[{'start':a,'end':b,'streams':sum(a<=s<=b for s in steps)} for a,b in bins],
            'interpretation':'All are false positives: the whole held-out stream is benign.'}
    # Marginal crossing rate differs from running-any-crossing probability.
    marginal=[]
    for key,records in traces.items():
        for step in records[0]['w_steps']:
            ws=[tr['w'][tr['w_steps'].index(step)] for tr in records]
            marginal.append({'pool':key,'query':step,'marginal_crossings':sum(w<1-threshold for w in ws),
                'marginal_rate':sum(w<1-threshold for w in ws)/len(records),
                'cumulative_rate':sum(first_crossing(tr,threshold,step) is not None for tr in records)/len(records)})
    return {'false_positive_timing':timing,
            'length_interpretation':'Nested prefixes of the same replayed streams at the original fixed threshold. Stream length, growing-set state, cumulative distance sample size and number of sequential tests co-vary; this does not isolate their causal effects.'},horizons,marginal


def diagnostic_plots(output, analysis, stream_rows, traces=None, horizons=None, marginal=None):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(1,2,figsize=(11,4),constrained_layout=True)
    for key,label in [('calibration','Calibration'),('benign','Held-out benign')]:
        values=np.sort([r['score'] for r in stream_rows if r['pool']==key])
        axes[0].step(values,np.arange(1,len(values)+1)/len(values),where='post',label=label)
    axes[0].axvline(analysis['threshold'],color='black',linestyle='--',label='Frozen P95')
    axes[0].set(xlabel='Maximum stream score',ylabel='Empirical CDF'); axes[0].legend(fontsize=8)
    features=analysis['stream_feature_comparisons']; labels=list(features)
    axes[1].bar(labels,[features[k]['source_groups'] for k in labels])
    axes[1].set(ylabel='Mean distinct source groups / stream',title='Descriptive composition; not a causal attribution')
    fig.savefig(output/'score_distributions_composition.png',dpi=170); plt.close(fig)
    if traces is None:
        return
    fig,axes=plt.subplots(1,3,figsize=(14,4),constrained_layout=True)
    for key,label in [('calibration','Calibration'),('benign','Held-out benign')]:
        subset=[r for r in marginal if r['pool']==key]
        axes[0].plot([r['query'] for r in subset],[r['cumulative_rate'] for r in subset],label=label+' cumulative')
        axes[0].plot([r['query'] for r in subset],[r['marginal_rate'] for r in subset],linestyle=':',label=label+' marginal')
        hs=[r for r in horizons if r['pool']==key and r['mean_kept_shapiro_samples'] is not None]
        axes[2].plot([r['horizon'] for r in hs],[r['mean_kept_shapiro_samples'] for r in hs],marker='o',label=label)
    axes[0].axhline(.05,color='gray',linestyle='--')
    axes[0].set(xlabel='Stream horizon / query',ylabel='Frozen-threshold false-positive fraction')
    axes[0].legend(fontsize=7)
    fp=[tr for tr in traces['benign'] if first_crossing(tr,analysis['threshold']) is not None]
    for tr in fp:
        axes[1].plot(tr['w_steps'],tr['w'],color='#377eb8',alpha=.22,linewidth=.7)
    axes[1].axhline(1-analysis['threshold'],color='black',linestyle='--')
    axes[1].set(xlabel='Query',ylabel='W',title=f'{len(fp)} false-positive benign trajectories')
    axes[2].set(xlabel='Stream horizon',ylabel='Mean retained cumulative distances',title='Three-sigma filtered Shapiro sample size')
    axes[2].legend(fontsize=8)
    fig.savefig(output/'benign_timing_length.png',dpi=170); plt.close(fig)
    fig,ax=plt.subplots(figsize=(8,4),constrained_layout=True)
    for prefix in analysis['prefixes']:
        ratio=prefix['requested_ratio']
        # Saved prefix W is diagnostic evidence; do not rerun mixed streams.
        saved=analysis['prefix_w_traces'][str(ratio)]
        ax.plot(range(102,111),saved,marker='o',label=f'{ratio:.0%} condition benign prefix')
    ax.axhline(1-analysis['threshold'],color='black',linestyle='--',label='Frozen W threshold')
    ax.set(xlabel='Query before common attack onset 111',ylabel='W',title='Different benign prefixes across attack-ratio conditions')
    ax.legend(fontsize=8)
    fig.savefig(output/'prefix_confounding.png',dpi=170); plt.close(fig)


def main(args):
    started=time.perf_counter()
    require(subprocess.check_output(['git','branch','--show-current'],cwd=ROOT,text=True).strip()==
            'experiment/stream-prada-order','Wrong branch')
    require(not args.output.exists(),'Refusing to overwrite Phase A output')
    args.output.mkdir(parents=True)
    metadata=json.loads((args.results/'metadata.json').read_text(encoding='utf-8'))
    # Existing integrity audit does not run the encoder or detector.
    from validate_results import validate
    validate(args.results)
    snapshot={str(p.relative_to(ROOT)):sha(p) for p in (ROOT/'stream_prada_order/results').rglob('*') if p.is_file()}
    pools,_=restore_data(metadata,args.data_root)
    indices=make_stream_indices(metadata['config'],pools)
    analysis,stream_rows=saved_analysis(args.results,metadata,pools,indices)
    examples=json.loads((args.results/'example_traces.json').read_text())
    analysis['prefix_w_traces']={key:[w for step,w in zip(value['random']['w_steps'],value['random']['w']) if step<=110]
                                 for key,value in examples.items()}
    write_csv(args.output/'stream_source_features.csv',stream_rows)
    traces=horizons=marginal=None
    if args.replay:
        write_json(args.output/'resource_preflight.json',{'announced_max_seconds':120,'expected_ram_bytes':2*1024**3,
            'expected_gpu_peak_bytes':1024**3,'purpose':'Recover missing timing and nested-horizon traces; unchanged frozen model, source, query membership and threshold.'})
        traces,timing_rows=replay_benign(args.results,metadata,pools,indices,args.output,args.model_root)
        replay,horizons,marginal=analyze_replay(traces,timing_rows,analysis['threshold'],metadata['config'])
        analysis.update(replay)
        write_csv(args.output/'horizon_diagnostics.csv',horizons)
        write_csv(args.output/'marginal_cumulative.csv',marginal)
        write_csv(args.output/'false_positive_streams.csv',[r for r in timing_rows if r['pool']=='benign' and r['alert']])
    write_json(args.output/'analysis.json',analysis)
    diagnostic_plots(args.output,analysis,stream_rows,traces,horizons,marginal)
    require(all(sha(ROOT/name)==h for name,h in snapshot.items()),'Existing evidence changed')
    provenance={'baseline_commit':'c1915e5517404df4963a0a20abb4a72c7df6e98a',
        'current_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        'original_evidence_sha256':snapshot,'analysis_source_sha256':sha(__file__),
        'detector_algorithm_modified':False,'test_threshold_tuned':False,
        'raw_datasets_committed':False,'seconds_including_analysis':time.perf_counter()-started}
    write_json(args.output/'provenance.json',provenance)
    write_json(args.output/'artifact_hashes.json',{p.name:sha(p) for p in sorted(args.output.iterdir()) if p.is_file()})
    print(json.dumps({'status':'completed','replayed':args.replay,'seconds':time.perf_counter()-started,
                      'false_positive_timing':analysis.get('false_positive_timing')}),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--results',type=Path,default=ROOT/'stream_prada_order/results/seed20261106_25min_retry1')
    parser.add_argument('--data-root',type=Path,default=ROOT.parent/'llm-mea/data/model_leeching')
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--replay',action='store_true')
    parser.add_argument('--model-root',type=Path,default=Path.home()/'.cache/huggingface/hub/models--BAAI--bge-small-en-v1.5/snapshots')
    main(parser.parse_args())
