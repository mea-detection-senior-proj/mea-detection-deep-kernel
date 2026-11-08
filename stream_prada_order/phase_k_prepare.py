"""Offline Phase K preparation only; no inference or grant creation entry point."""
import argparse
import copy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT=Path(__file__).resolve()
while not (ROOT/'stream_prada_order').is_dir():ROOT=ROOT.parent
sys.path.insert(0,str(ROOT))
from stream_prada_order.traffic_collection.schema import IntegrityError
from stream_prada_order.traffic_runtime.policy import profile, limits, load_grant, checkout_status, code_digest


def preparation_documents(head):
    if not isinstance(head,str) or not re.fullmatch('[a-f0-9]{40}',head):raise ValueError('exact_preparation_head_required')
    p=profile();budget={k:limits()[k] for k in ['max_requests','max_attempts','max_attempts_per_request',
        'max_query_bytes','max_response_bytes','max_logical_storage_bytes']}
    budget['max_session_attempts']=4
    cfg={'schema_version':'traffic-manifest-v1','run_id':None,'traffic_kind':'real','label':'benign',
         'collector_revision':None,'protocol_sha256':None,'actor_sha256':None,'source_group_sha256':None,
         'victim':copy.deepcopy(p['identity']),'authorization':{'record_id':None,'evidence_sha256':None},
         'sources':None,'task_ids':None,'split':'development','acquisition':None,'budget':budget,
         'retry_policy':'not_sent_only'}
    plan={'schema_version':'qwen-query-plan-v1','run_id':None,'session_id':None,'native_session_sha256':None,'queries':None}
    def draft(document):
        return {'schema_version':'phase-k-nonexecutable-draft-v1','prepared_on_head':head,
                'execution_authorized':False,'status':'OPERATOR_INPUTS_REQUIRED','document':document}
    return {'manifest':draft(cfg),'query_plan':draft(plan),'requirements':{
        'schema_version':'phase-k-operator-requirements-v1','execution_authorized':False,'grant_sha256':None,
        'evidence_categories':['operator_authorization','model_license','source_authorization','privacy_review'],
        'native_session_count':1,'planned_request_count':None,'input_tokens':None,'output_tokens':None,
        'limits':limits(),'code_sha256':code_digest(),'chat_template_sha256':p['chat_template_sha256'],
        'grant_schema':'qwen-execution-grant-v1','grant_validity_max_hours':24,
        'grant_requirements':'Exact operator-reviewed manifest/ordered query plan bindings, real scope, UTC validity, independent raw grant SHA; no generated approval.',
        'query_requirements':'1-4 actual operator-owned legitimate requests from one native session; exact UTF-8 bytes/order/source/task/format and namespaced actor/native-session HMAC with key outside Git.',
        'privacy_requirements':'Review ACL, retention, deletion authority, backup/encryption, key handling, read-only snapshot and protected one-shot registry; private evidence contents must be reviewed.',
        'runtime_entry':'RuntimeStore -> LocalQwenAdapter -> RuntimeCollector; default real execution disabled',
        'finalize_only_on_clean_execution_head':True}}


def approval_refusals(acquisition_record):
    # Only negative checks: no grant/claim is ever created by this module.
    result={'missing_grant_refused':False,'acquisition_grant_refused':None,'claim_created':False}
    try:load_grant(None,None,None,None)
    except IntegrityError as exc:
        result.update(missing_grant_refused=True,missing_grant_code=str(exc))
    if acquisition_record is not None:
        path=Path(acquisition_record)
        if path.stat().st_size>65536:raise ValueError('approval_metadata_too_large')
        sha=hashlib.sha256(path.read_bytes()).hexdigest()
        try:load_grant(path,sha,None,None)
        except IntegrityError as exc:
            result.update(acquisition_grant_refused=True,acquisition_rejection_code=str(exc),acquisition_record_sha256=sha)
        else:raise RuntimeError('acquisition_record_unexpectedly_accepted')
    if not result['missing_grant_refused']:raise RuntimeError('missing_grant_unexpectedly_accepted')
    return result


def offline_check(snapshot,store,acquisition_record=None):
    from stream_prada_order.phase_i_check import verify_frozen
    from stream_prada_order.traffic_runtime.readiness import readiness
    from stream_prada_order.traffic_collection.store import check_private_root, _check_ignored_paths
    checkout=checkout_status()
    if not (checkout['branch']=='experiment/stream-prada-order' and checkout['clean'] and checkout['main_unchanged']):
        raise ValueError('clean_isolated_checkout_required')
    store=Path(store);check_private_root(store)
    if not store.is_dir() or store.is_symlink() or any(store.iterdir()):raise ValueError('dedicated_empty_store_required')
    for parent in store.parents:
        if parent==ROOT:break
        if parent.is_symlink():raise ValueError('private_store_symlink_parent')
    _check_ignored_paths(store,['runtime_receipts/probe.prepared.private','runtime_receipts/probe.outcome.private'])
    manifests={}
    for phase in 'GHIJ':
        path=ROOT/'stream_prada_order'/f'PHASE_{phase}_MANIFEST.json';data=json.loads(path.read_bytes())
        for name,item in data['files'].items():
            if hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=item['sha256']:raise ValueError('prior_manifest_mismatch')
        manifests[phase]={'files_verified':len(data['files']),'manifest_sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
    ready=readiness(snapshot=Path(snapshot),storage_root=store)
    return {'schema_version':'phase-k-offline-preflight-v1','observed_utc':datetime.now(timezone.utc).isoformat(),
        'checkout':checkout,'frozen':verify_frozen(),'manifests':manifests,'readiness':ready,
        'grant_negative_checks':approval_refusals(acquisition_record),'private_store_empty':not any(store.iterdir()),
        'torch_or_transformers_imported':any(x in sys.modules for x in ['torch','transformers']),
        'model_weights_loaded':0,'tokenizers_instantiated':0,'real_requests':0,'claims_created':0,
        'pilot_executed':False,'larger_collection_decision':'NO-GO','reason':'Actual benign session, operator execution grant and privacy/source records are pending.'}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--snapshot',type=Path,required=True);parser.add_argument('--storage-root',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True);parser.add_argument('--acquisition-record',type=Path)
    args=parser.parse_args()
    from stream_prada_order.traffic_collection.store import _check_ignored_paths
    names=['preflight.json','manifest.draft.json','query_plan.draft.json','operator_requirements.json']
    _check_ignored_paths(args.output,names)
    if args.output.exists():raise ValueError('new_output_directory_required')
    receipt=offline_check(args.snapshot,args.storage_root,args.acquisition_record)
    docs=preparation_documents(receipt['checkout']['head']);args.output.mkdir(parents=True)
    values=[receipt,docs['manifest'],docs['query_plan'],docs['requirements']]
    for name,value in zip(names,values):
        with (args.output/name).open('x',encoding='utf-8',newline='\n') as f:json.dump(value,f,indent=2,ensure_ascii=True);f.write('\n')
    print(json.dumps({'output':str(args.output),'readiness_status':receipt['readiness']['status'],
        'codes':receipt['readiness']['codes'],'snapshot':receipt['readiness']['snapshot'],
        'resources':receipt['readiness']['resources'],'grant_negative_checks':receipt['grant_negative_checks'],
        'real_execution_enabled':False,'pilot_executed':False},indent=2))
    return 0 if receipt['readiness']['snapshot']['status']=='passed' and receipt['readiness']['environment']['status']=='passed_static_only' else 2

if __name__=='__main__':raise SystemExit(main())
