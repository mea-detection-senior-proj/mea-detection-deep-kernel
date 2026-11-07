"""Bounded integer-program certificate for the small article-group cover gap."""
import argparse
import gzip
import json
from pathlib import Path
import time

import numpy as np
from scipy.optimize import Bounds, LinearConstraint, milp
from scipy.sparse import lil_matrix

import phase_b_feasibility as fb


def prove_capacity(groups,b,a,lower,upper,seconds=5):
    if lower==upper:
        return {'lower':lower,'upper':upper,'status':'already_certified'}
    dominant=[g for g in groups if len(g['B'])>=b and len(g['A'])>=a]
    small=[g for g in groups if g not in dominant]
    # A group satisfying a whole cohort alone never benefits from using helpers.
    k=upper-len(dominant); n=len(small)
    require=k>0 and n>0
    if not require: return {'lower':lower,'upper':upper,'status':'unresolved'}
    labels=[(label,target) for label,target in [('B',b),('A',a)] if target]
    matrix=lil_matrix((n+len(labels)*k,n*k),dtype=float)
    lo=np.full(matrix.shape[0],-np.inf); hi=np.full(matrix.shape[0],np.inf)
    for i in range(n):
        for j in range(k): matrix[i,i*k+j]=1
        hi[i]=1
    row=n
    for label,target in labels:
        for j in range(k):
            for i,g in enumerate(small): matrix[row,i*k+j]=len(g[label])
            lo[row]=target; row+=1
    start=time.perf_counter()
    result=milp(np.zeros(n*k),integrality=np.ones(n*k),bounds=Bounds(0,1),
                constraints=LinearConstraint(matrix.tocsr(),lo,hi),options={'time_limit':seconds})
    out={'lower':lower,'upper':upper,'solver_status':int(result.status),
         'solver_message':str(result.message),'seconds':time.perf_counter()-start,
         'dominant_groups_fixed_to_single_cohorts':len(dominant),'remaining_groups':n,
         'status':'unresolved'}
    if result.status==2:
        out.update(upper=upper-1,status='optimal_certified' if upper-1==lower else 'upper_bound_tightened')
    elif result.status==0:
        cohorts=[]
        for g in dominant:
            cohorts.append({'groups':[g['id']],'B':g['B'][:b],'A':g['A'][:a],'required_B':b,'required_A':a})
        for j in range(k):
            selected=[g for i,g in enumerate(small) if result.x[i*k+j]>.5]
            cohorts.append({'groups':[g['id'] for g in selected],
                'B':sorted({h for g in selected for h in g['B']})[:b],
                'A':sorted({h for g in selected for h in g['A']})[:a],
                'required_B':b,'required_A':a})
        fb.validate_allocation(cohorts)
        out.update(lower=len(cohorts),status='optimal_certified',cohorts=cohorts)
    return out


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--audit',type=Path,default=fb.ROOT/'stream_prada_order/diagnostics/phase_b_verified')
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    fb.require(not args.output.exists(),'Refusing to overwrite proof')
    groups=json.loads(gzip.decompress((args.audit/'source_groups.json.gz').read_bytes()))['article']
    groups=[{'id':g['id'],**g['by_dataset']['model_leeching']} for g in groups
            if g['known_article'] and any(g['by_dataset']['model_leeching'].values())]
    capacity=next(r for r in json.loads((args.audit/'capacity.json').read_text())
                  if r['dataset']=='model_leeching' and r['grouping']=='article')
    out={}
    for name,case in capacity['cases'].items():
        proof=prove_capacity(groups,case['required_benign'],case['required_attack'],case['constructed'],case['capacity_upper_bound'])
        out[name]=proof
    fb.write(args.output,{'proofs':out,'source_sha256':fb.sha(__file__),
                         'input_groups_sha256':fb.sha(args.audit/'source_groups.json.gz'),'detector_runs':0,'encoder_runs':0})
    print(json.dumps({k:{x:y for x,y in v.items() if x!='cohorts'} for k,v in out.items()},indent=2))
