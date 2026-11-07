"""CPU-only cohort construction certificates; no encoder or detector execution.

Passage groups and mapped Wikipedia article groups are separate audits. Counts
are achieved constructive lower bounds unless they meet the proved capacity
upper bound; statistical independence is never inferred from text disjointness.
"""
import argparse
from collections import Counter,defaultdict
import gzip
import hashlib
import json
import math
from pathlib import Path
import subprocess
import time
import unicodedata

from failure_analysis import connected_components

ROOT=Path(__file__).resolve().parents[1]
DATASETS=('model_leeching','ME_BERT_boolq_wiki')
EXPECTED={
 ('model_leeching','normal'):'2c7b6377db11481d0708607a972b94d8aa0ad0fc16d7c842881773fd4fc7fb77',
 ('model_leeching','attacker'):'ac90d6f69cadfa5c960f35bb71ad909983842939adfb5dcbc9f327ca13bbb942',
 ('ME_BERT_boolq_wiki','normal'):'276ea0cbb06f1992f5877aa727f3e7f421984536201347cb278b7be94c6e95a4',
 ('ME_BERT_boolq_wiki','attacker'):'f29c09558fac9c083ac06dab10ac853bae164107ea369a99c45995454cd8b759'}
SQUAD={
 'squad_train_v1.1.json':('https://rajpurkar.github.io/SQuAD-explorer/dataset/train-v1.1.json','3527663986b8295af4f7fcdff1ba1ff3f72d07d61a20f487cb238a6ef92fd955'),
 'squad_dev_v1.1.json':('https://rajpurkar.github.io/SQuAD-explorer/dataset/dev-v1.1.json','95aa6a52d5d6a735563366753ca50492a658031da74f301ac5238b03966972c9')}


def require(ok,message):
    if not ok: raise ValueError(message)


def norm(text): return ' '.join(unicodedata.normalize('NFKC',text).casefold().split())
def digest(text): return hashlib.sha256(text.encode()).hexdigest()
def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def write(path,obj): Path(path).write_text(json.dumps(obj,indent=2,ensure_ascii=False,allow_nan=False),encoding='utf-8',newline='\n')


def boolq_passage(query):
    require(query.startswith('Passage: ') and '\nQuestion: ' in query,'Unrecognized BoolQ processed query')
    return query[len('Passage: '):].rsplit('\nQuestion: ',1)[0].strip()


def model_passage(query):
    require(query.startswith('Given this context:') and 'Can you answer this question briefly:' in query,
            'Unrecognized model_leeching attack query')
    wrapped=query.split('Can you answer this question briefly:',1)[0].removeprefix('Given this context:').strip()
    require(wrapped.startswith('"') and wrapped.endswith('"'),'Missing context wrapper')
    return wrapped[1:-1]


def zero_fp_upper(n,alpha=.05):
    require(n>0,'Positive sample size required')
    return float(1-alpha**(1/n))


def eligible_groups(groups,strict=False):
    return [g for g in groups if not strict or g['known_article']]


def upper_bound(groups,b,a):
    limits=[]
    for label,target in [('B',b),('A',a)]:
        if target: limits.append(sum(min(len(g[label]),target) for g in groups)//target)
    return min(limits)


def choose_subset(groups,label,target):
    if target<=0: return []
    # A source with >target queries may supply only one cohort; excess is unused.
    cap=2*target-1; mask=(1<<(cap+1))-1; reachable=1; parents={}
    for g in sorted(groups,key=lambda g:g['id']):
        weight=min(len(g[label]),target)
        if not weight: continue
        new=((reachable<<weight)&mask)&~reachable
        bits=new
        while bits:
            bit=bits&-bits; value=bit.bit_length()-1
            parents[value]=(value-weight,g['id']); bits-=bit
        reachable|=new
        if reachable&(1<<target): break
    sums=[s for s in range(target,cap+1) if reachable&(1<<s)]
    if not sums: return None
    value=min(sums); result=[]
    while value:
        previous,gid=parents[value]; result.append(gid); value=previous
    return result


def allocate(groups,requirements):
    available={g['id']:g for g in groups}; output=[]
    for b,a in requirements:
        selected=[]
        for label,target in [('B',b),('A',a)]:
            supplied=sum(len(available[g][label]) for g in selected)
            if supplied>=target: continue
            chosen=choose_subset([g for gid,g in available.items() if gid not in selected],label,target-supplied)
            if chosen is None: return output,list(available.values())
            selected+=chosen
        row={'groups':sorted(selected),'B':[],'A':[],'required_B':b,'required_A':a}
        for label,target in [('B',b),('A',a)]:
            row[label]=sorted({h for gid in selected for h in available[gid][label]})[:target]
            require(len(row[label])==target,'Insufficient deduplicated cohort queries')
        output.append(row)
        for gid in selected: del available[gid]
    validate_allocation(output)
    return output,list(available.values())


def validate_allocation(cohorts):
    used_groups=set(); used_queries=set()
    for cohort in cohorts:
        gs=set(cohort['groups']); qs=cohort['B']+cohort['A']
        require(not used_groups&gs,'Source group used in multiple cohorts/splits')
        require(not used_queries&set(qs),'Query used in multiple cohorts/splits')
        require(len(set(qs))==len(qs),'Duplicate/cross-label query inside cohort')
        require(len(cohort['B'])==cohort['required_B'] and len(cohort['A'])==cohort['required_A'],'Cohort size mismatch')
        used_groups|=gs; used_queries|=set(qs)


def load_records(data_root,cache):
    lookup={}; passage_titles=defaultdict(set); source_metadata={}
    for name,(url,expected) in SQUAD.items():
        path=cache/name; require(path.exists(),f'Missing official lookup file: {path}')
        require(sha(path)==expected,'Official SQuAD lookup drift')
        source_metadata[name]={'url':url,'sha256':expected,'bytes':path.stat().st_size}
        for article in json.loads(path.read_text(encoding='utf-8'))['data']:
            title=norm(article['title'].replace('_',' '))
            for paragraph in article['paragraphs']:
                context=norm(paragraph['context']); passage_titles[context].add(title)
                for q in paragraph['qas']: lookup[q['id']]=(title,norm(q['question']),context)
    records=[]; audit={}; inputs={}
    for dataset in DATASETS:
        for kind,label in [('normal','B'),('attacker','A')]:
            path=data_root/dataset/kind/'queries.jsonl'
            require(sha(path)==EXPECTED[(dataset,kind)],'Processed dataset hash drift')
            inputs[f'{dataset}/{kind}']={'sha256':sha(path),'bytes':path.stat().st_size}
            count=known=0; titles=set()
            for line in path.open(encoding='utf-8'):
                row=json.loads(line); query=norm(row['query']); title=None; passage=None
                if dataset=='model_leeching':
                    require(row['id'] in lookup,'Unmatched model_leeching question ID')
                    title,question,official_passage=lookup[row['id']]
                    if label=='B': require(query==question,'Question text differs from official SQuAD ID')
                    else: require(norm(model_passage(row['query']))==official_passage,'Attack context differs from official SQuAD ID')
                    passage=official_passage
                else:
                    passage=norm(boolq_passage(row['query']))
                    possible=passage_titles.get(passage,set())
                    if len(possible)==1: title=next(iter(possible))
                if title is not None: known+=1; titles.add(title)
                records.append({'dataset':dataset,'label':label,'id':row['id'],
                                'q':digest(query),'p':digest(passage),'title':title})
                count+=1
            audit[f'{dataset}/{kind}']={'rows':count,'unique_texts':len({r['q'] for r in records if r['dataset']==dataset and r['label']==label}),
                'unique_ids':len({r['id'] for r in records if r['dataset']==dataset and r['label']==label}),
                'article_mapped_rows':known,'distinct_mapped_titles':len(titles)}
    return records,{'processed_files':inputs,'official_lookup_files':source_metadata,'row_audit':audit,
                    'boolq_original_title_lookup':'Original Google bucket train.jsonl returned HTTP 403; no title guesses. Exact passage matches to official SQuAD only are eligible for article mapping.'}


def grouped_records(records,mode,exposed):
    labels=defaultdict(set)
    for r in records: labels[r['q']].add(r['label'])
    ambiguous={q for q,ls in labels.items() if len(ls)>1}
    keys=[]
    for r in records:
        rowkeys=[('id',r['dataset'],r['id']),('query',r['q']),('passage',r['p'])]
        if mode=='article' and r['title'] is not None: rowkeys.append(('wikipedia_article',r['title']))
        keys.append(rowkeys)
    components=connected_components(keys); members=defaultdict(list)
    for r,c in zip(records,components): members[c].append(r)
    groups=[]
    for rows in members.values():
        gid=digest('\0'.join(sorted({r['q'] for r in rows})))
        group={'id':gid,'known_article':all(r['title'] is not None for r in rows),
               'titles':sorted({digest(r['title']) for r in rows if r['title'] is not None}),
               'exposed_phase_a':any(r['q'] in exposed for r in rows),'by_dataset':{}}
        for dataset in DATASETS:
            group['by_dataset'][dataset]={label:sorted({r['q'] for r in rows if r['dataset']==dataset and r['label']==label and r['q'] not in ambiguous}) for label in ('B','A')}
        groups.append(group)
    return sorted(groups,key=lambda g:g['id']),ambiguous


def save_cohorts(path,cohorts):
    validate_allocation(cohorts)
    data=json.dumps(cohorts,separators=(',',':')).encode()
    path.write_bytes(gzip.compress(data,mtime=0))


def capacity_case(groups,b,a,path):
    upper=upper_bound(groups,b,a)
    cohorts,_=allocate(groups,[(b,a)]*upper)
    save_cohorts(path,cohorts)
    return {'constructed':len(cohorts),'capacity_upper_bound':upper,
            'optimality':'certified_by_matching_upper_bound' if len(cohorts)==upper else 'constructive_lower_bound_only',
            'required_benign':b,'required_attack':a,'certificate':path.name}


def main(args):
    started=time.perf_counter()
    require(subprocess.check_output(['git','branch','--show-current'],cwd=ROOT,text=True).strip()=='experiment/stream-prada-order','Wrong branch')
    require(not args.output.exists(),'Refusing to overwrite Phase B output')
    args.output.mkdir(parents=True)
    records,provenance=load_records(args.data_root,args.source_cache)
    baseline=json.loads((ROOT/'stream_prada_order/results/seed20261106_25min_retry1/metadata.json').read_text())
    exposed=set(sum(baseline['pool_query_sha256'].values(),[]))
    results=[]; group_manifest={}; allocations=[]
    for mode in ('passage','article'):
        global_groups,ambiguous=grouped_records(records,mode,exposed)
        group_manifest[mode]=global_groups
        for dataset in DATASETS:
            ds_groups=[{'id':g['id'],**g['by_dataset'][dataset],'known_article':g['known_article'],
                        'exposed_phase_a':g['exposed_phase_a']} for g in global_groups if any(g['by_dataset'][dataset].values())]
            active=eligible_groups(ds_groups,strict=mode=='article')
            row={'dataset':dataset,'grouping':mode,'global_groups':len(ds_groups),'eligible_groups':len(active),
                 'unique_benign':sum(len(g['B']) for g in active),'unique_attack':sum(len(g['A']) for g in active),
                 'groups_exposed_phase_a':sum(g['exposed_phase_a'] for g in active),
                 'phase_a_unexposed_groups':sum(not g['exposed_phase_a'] for g in active),
                 'ambiguous_query_hashes_removed_globally':len(ambiguous),'cases':{}}
            for name,b,a in [('benign',256,0),('pure_attack',0,256),('paired_control_mixed',256,128)]:
                path=args.output/f'cohorts_{mode}_{dataset}_{name}.json.gz'
                row['cases'][name]=capacity_case(active,b,a,path)
            scenarios=[(20,5,14),(20,4,10),(20,2,2),(12,3,6),(10,3,6),(8,2,4)]
            for ncal,nval,ntest in scenarios:
                requirements=[(256,0)]*ncal+[(256,128)]*(nval+ntest)
                cohorts,_=allocate(active,requirements)
                complete=len(cohorts)==len(requirements)
                name=f'plan_{mode}_{dataset}_{ncal}_{nval}_{ntest}.json.gz'
                if complete:
                    for i,c in enumerate(cohorts): c['split']='calibration' if i<ncal else ('validation' if i<ncal+nval else 'final_test')
                    save_cohorts(args.output/name,cohorts)
                allocations.append({'dataset':dataset,'grouping':mode,'requested_calibration':ncal,'requested_validation':nval,
                    'requested_final_test':ntest,'constructed_cohorts':len(cohorts),'feasible':complete,
                    'certificate':name if complete else None,
                    'zero_fp_final_one_sided_95_upper':zero_fp_upper(ntest) if complete else None,
                    'fresh_final_test_certified':False})
            remaining=[g for g in active if not g['exposed_phase_a']]
            row['phase_a_unexposed_only']={name:capacity_case(remaining,b,a,args.output/f'unexposed_{mode}_{dataset}_{name}.json.gz')
                                         for name,b,a in [('benign',256,0),('paired',256,128)]}
            results.append(row)
    # Quantify the distinction between article titles and transitive components.
    title_by_query={r['q']:r['title'] for r in records if r['dataset']=='model_leeching' and r['label']=='B'}
    cal={title_by_query[q] for q in baseline['pool_query_sha256']['calibration']}
    test={title_by_query[q] for q in baseline['pool_query_sha256']['benign']}
    model_titles={r['title'] for r in records if r['dataset']=='model_leeching' and r['title'] is not None}
    cross={'model_article_titles':len(model_titles),'phase_a_calibration_titles':len(cal),'phase_a_test_titles':len(test),
           'phase_a_calibration_test_shared_titles':len(cal&test),'phase_a_exposed_titles_union':len(cal|test),
           'components_with_both_datasets':{mode:sum(all(any(g['by_dataset'][ds].values()) for ds in DATASETS) for g in gs) for mode,gs in group_manifest.items()},
           'unmapped_boolq_articles_are_not_certified_disjoint':True}
    write(args.output/'capacity.json',results); write(args.output/'allocation_scenarios.json',allocations)
    write(args.output/'source_overlap.json',cross)
    (args.output/'source_groups.json.gz').write_bytes(gzip.compress(json.dumps(group_manifest,separators=(',',':')).encode(),mtime=0))
    # Distribution-free exact bound for zero failures under independent Bernoulli cohorts.
    uncertainty=[{'n':n,'zero_fp_one_sided_95_upper':zero_fp_upper(n),'minimum_rate_step':1/n,
                  'linear_p95_rank_zero_based':.95*(n-1)} for n in [5,6,8,10,12,14,20,24,30,36,38,59,100,200,299]]
    write(args.output/'uncertainty.json',uncertainty)
    provenance.update({'branch':'experiment/stream-prada-order','baseline_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
                       'analysis_source_sha256':sha(__file__),'phase_a_metadata_sha256':sha(ROOT/'stream_prada_order/results/seed20261106_25min_retry1/metadata.json'),
                       'detector_runs':0,'encoder_runs':0,'seconds':time.perf_counter()-started,
                       'note':'Capacity cases are alternative uses of the same rows, not additive. Group disjointness is operational and does not prove statistical independence. Unmapped article sources are excluded in strict article mode.'})
    write(args.output/'provenance.json',provenance)
    write(args.output/'artifact_hashes.json',{p.name:sha(p) for p in sorted(args.output.iterdir()) if p.is_file()})
    print(json.dumps({'capacity':results,'source_overlap':cross,'seconds':time.perf_counter()-started},indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-root',type=Path,default=ROOT.parent/'llm-mea/data')
    parser.add_argument('--source-cache',type=Path,default=Path.home()/'.cache/stream-prada-phase-b')
    parser.add_argument('--output',type=Path,required=True)
    main(parser.parse_args())
