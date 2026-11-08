"""Bounded metadata/header inspection only; never joins or evaluates real scores."""
import argparse
import csv
from datetime import datetime,timezone
import gzip
import hashlib
import io
import json
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[1]


def raw(path,cap=4*1024**2):
    with path.open('rb') as f:value=f.read(cap+1)
    if len(value)>cap:raise ValueError('audit_read_cap')
    return value


def identify(path,value):
    return {'path':path.relative_to(ROOT).as_posix(),'bytes':len(value),'sha256':hashlib.sha256(value).hexdigest()}


def inspect():
    def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT).decode().strip()
    assert git('branch','--show-current')=='experiment/stream-prada-order'
    assert git('rev-parse','main')=='5fb5e07d750a73a0a663a174433bab931ae7568a'
    result={'schema_version':'hybrid-integration-metadata-audit-v1','observed_utc':datetime.now(timezone.utc).isoformat(),
        'branch':git('branch','--show-current'),'base_head':git('rev-parse','HEAD'),
        'scope':'Explicit saved development metadata, one validation control trace shape, CSV headers and producer sources; no evaluation outcomes or private traffic.',
        'scientific_evaluation':False,'real_exports_generated':0,'real_score_joins':0,'model_or_detector_execution':False}
    source_paths=['stream_prada_order/experiment.py','stream_prada_order/phase_c_runner.py','stream_prada_order/phase_d_pilot.py',
                  'pilot/deep_kernel_pilot.py','MMD_detection/mmd_detector_gpu.py','pilot/README.md',
                  'stream_prada_order/hybrid_fusion.py','stream_prada_order/hybrid_fusion_config_v1.json','stream_prada_order/PHASE_F_PROTOCOL_TH.md']
    result['sources']=[identify(ROOT/p,raw(ROOT/p)) for p in source_paths]
    pilot=ROOT/'pilot/outputs'
    result['deep_kernel_configured_output']={'path':'pilot/outputs','exists':pilot.exists(),
        'status':'missing_in_this_checkout' if not pilot.exists() else 'requires_explicit_per_run_inspection',
        'no_machine_wide_search':True}
    p=ROOT/'stream_prada_order/results/phase_c_pilot_20261107_v1/metadata.json';b=raw(p);meta=json.loads(b)
    cert=ROOT/meta['config']['cohort_certificate'];cb=raw(cert)
    result['sequential_metadata']={**identify(p,b),'encoder':meta['config']['model'],'encoder_revision':meta['config']['model_revision'],
        'stream_length':meta['config']['stream_length'],'source_certificate':identify(cert,cb),
        'certificate_hash_matches_config':hashlib.sha256(cb).hexdigest()==meta['config']['certificate_sha256'],
        'native_session_or_availability_evidence':False,'certificate_scope':'Historical article/cohort allocation; not a native user/run connected-group certificate.'}
    p=p.parent/'embedding_calibration_validation.json';b=raw(p);emb=json.loads(b)
    result['sequential_embedding_metadata']={**identify(p,b),**{k:emb[k] for k in ['queries','query_order_sha256','raw_text_order_sha256','embedding_sha256']},
        'missing':['per-row vector hashes','shared canonical request/query manifest','per-cohort-local-index to common embedding-row mapping']}
    p=p.parent/'control_trace_12.json.gz';b=raw(p,1024**2)
    with gzip.GzipFile(fileobj=io.BytesIO(b)) as f:decoded=f.read(1024**2+1)
    if len(decoded)>1024**2:raise ValueError('trace_schema_read_cap')
    trace=json.loads(decoded)
    result['sequential_trace_shape']={**identify(p,b),'keys':list(trace),'order_length':len(trace['order']),
        'w_count':len(trace['w']),'query_index_range':[trace['w_steps'][0],trace['w_steps'][-1]],
        'score_values_exported_or_evaluated':False}
    p=ROOT/'stream_prada_order/results/phase_d_pilot_20261107_v2/per_stream.csv.gz';b=raw(p)
    with gzip.GzipFile(fileobj=io.BytesIO(b)) as f:header=f.readline(8193)
    if len(header)>8192:raise ValueError('header_cap')
    result['cusum_saved_output']={**identify(p,b),'header':next(csv.reader([header.decode().strip()])),
        'checkpoint_curves_present':False,'recomputation_performed':False}
    p=ROOT/'experiment_result/main/seed=42/MMD/model_leeching_bge_bs1500/metadata.json';b=raw(p);m=json.loads(b)
    fields=['dataset','embedding_model','query_prefix','normalize_embeddings','batch_size','reference_repeats','seed']
    result['mmd_saved_metadata']={**identify(p,b),'keys':list(m),'declared_settings':{k:m.get(k) for k in fields},
        'kind':'Existing MMD batch run; Deep Kernel checkpoint not established by this metadata',
        'missing':['session/request chronology','canonical ordered-query manifest','exact encoder/tokenizer revision',
                   'per-row embedding hashes/index mapping','connected source/user/run split certificate',
                   'window start/end and actual member hashes','availability/computed-through provenance',
                   'per-window reference draw IDs','learned-kernel checkpoint/configuration digest']}
    p=p.with_name('batch_scores.csv');b=raw(p)
    result['mmd_saved_scores']={**identify(p,b),'header':next(csv.reader(io.StringIO(b.decode('utf-8-sig')))),
        'rows_joined_or_evaluated':0,'batch_ids_are_not_session_ids':True}
    result['decision']='NO-GO genuine same-stream integration; metadata blockers confirmed within inspected scope'
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    if args.output.exists():raise ValueError('new_output_required')
    result=inspect();args.output.parent.mkdir(parents=True,exist_ok=True)
    with args.output.open('x',encoding='utf-8',newline='\n') as f:json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps({'output':str(args.output),'decision':result['decision'],'real_score_joins':0}))

if __name__=='__main__':main()
