"""Frozen profile and explicit, expiring, hash-bound operator grant validation."""
import copy
from datetime import datetime, timezone
import hashlib
import os
from pathlib import Path
import re
import subprocess

from ..traffic_collection.schema import require, strict_json, canonical, digest, validate_manifest, ExecutionDisabled

HERE=Path(__file__).resolve().parent


def read_json(path, cap=65536):
    with Path(path).open('rb') as f:raw=f.read(cap+1)
    require(len(raw)<=cap,'metadata_size_exceeded')
    return strict_json(raw)


def profile():return read_json(HERE/'profile_v1.json')
def limits():return profile()['limits']
def snapshot_lock():return read_json(HERE/'snapshot_lock_v1.json')
def environment_lock():return read_json(HERE/'environment_lock_v1.json')


def file_digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def code_digest():
    paths=[*sorted(HERE.glob('*.py')),*sorted(HERE.glob('*_v1.json')),
           *sorted((HERE.parent/'traffic_collection').rglob('*.py')),
           *sorted((HERE.parent/'traffic_collection'/'schemas').glob('*.json'))]
    return digest(canonical({p.relative_to(HERE.parent).as_posix():file_digest(p) for p in paths}))


def bindings(manifest,plan):
    return {'code_sha256':code_digest(),'profile_sha256':file_digest(HERE/'profile_v1.json'),
            'snapshot_lock_sha256':file_digest(HERE/'snapshot_lock_v1.json'),
            'environment_lock_sha256':file_digest(HERE/'environment_lock_v1.json'),
            'manifest_sha256':digest(canonical(manifest)),'query_plan_sha256':digest(canonical(plan))}


def checkout_status():
    root=HERE.parent.parent
    def git(*args):return subprocess.check_output(['git',*args],cwd=root,timeout=3,stderr=subprocess.DEVNULL).decode().strip()
    branch=git('branch','--show-current');head=git('rev-parse','HEAD')
    clean=not git('status','--porcelain','--untracked-files=normal')
    return {'branch':branch,'head':head,'clean':clean,
            'main_unchanged':git('rev-parse','main')=='5fb5e07d750a73a0a663a174433bab931ae7568a'}


def _exact(value,keys,code='policy_invalid'):
    require(type(value) is dict and set(value)==set(keys),'policy_invalid')


def validate_manifest_plan(manifest,plan):
    validate_manifest(manifest)
    require(manifest['traffic_kind'] in {'mock','real'} and manifest['label']=='benign'
            and manifest['acquisition'] is None and manifest['split']=='development','benign_pilot_only')
    require(manifest['victim']==profile()['identity'],'victim_revision_mismatch')
    b=manifest['budget'];l=limits()
    require(all(b[key]<=l[key] for key in ['max_requests','max_attempts','max_attempts_per_request',
                                         'max_query_bytes','max_response_bytes','max_logical_storage_bytes']), 'pilot_budget_exceeded')
    require(b['max_session_attempts']<=4 and b['max_attempts_per_request']==1,'pilot_no_retry')
    _exact(plan,['schema_version','run_id','session_id','native_session_sha256','queries'])
    require(plan['schema_version']=='qwen-query-plan-v1' and plan['run_id']==manifest['run_id'],'plan_run_mismatch')
    require(re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.:-]{0,95}',plan['session_id']) is not None,'plan_session_invalid')
    require(re.fullmatch(r'[a-f0-9]{64}',plan['native_session_sha256']) is not None,'plan_native_invalid')
    require(type(plan['queries']) is list and 1<=len(plan['queries'])<=b['max_requests'],'plan_budget_invalid')
    ids=set()
    for q in plan['queries']:
        _exact(q,['request_id','query_sha256','document_ids','task_id','format_class'])
        require(type(q['request_id']) is str and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.:-]{0,95}',q['request_id']) is not None,'plan_request_invalid')
        require(q['request_id'] not in ids,'plan_duplicate_request');ids.add(q['request_id'])
        require(type(q['query_sha256']) is str and re.fullmatch(r'[a-f0-9]{64}',q['query_sha256']) is not None,'plan_query_hash_invalid')
        require(type(q['document_ids']) is list and bool(q['document_ids']) and len(set(q['document_ids']))==len(q['document_ids'])
                and set(q['document_ids'])<={s['document_id'] for s in manifest['sources']},'plan_source_invalid')
        require(q['task_id'] in manifest['task_ids'] and q['format_class'] in {'question_only','context_request','code','mixed','other'},'plan_task_format_invalid')


class Grant:
    """Validated operator reference, not a digital signature or proof of consent."""
    def __init__(self,record,sha):self.record,self.sha=copy.deepcopy(record),sha

    def check(self,manifest,plan,now=None):
        require(self.record['bindings']==bindings(manifest,plan),'grant_binding_mismatch')
        current=now or datetime.now(timezone.utc)
        issued=datetime.fromisoformat(self.record['issued_utc'].replace('Z','+00:00'))
        expires=datetime.fromisoformat(self.record['expires_utc'].replace('Z','+00:00'))
        require(issued.tzinfo is not None and expires.tzinfo is not None and
                issued<=current<expires and (expires-issued).total_seconds()<=86400,'grant_expired_or_not_active')


def load_grant(path,expected_sha256,manifest,plan,evidence_root=None,now=None):
    if not path or not expected_sha256:raise ExecutionDisabled('explicit_execution_grant_required')
    with Path(path).open('rb') as f:raw=f.read(65537)
    require(len(raw)<=65536 and digest(raw)==expected_sha256,'grant_hash_mismatch')
    record=strict_json(raw)
    _exact(record,['schema_version','grant_id','purpose','traffic_kind','execution_authorized',
                   'issued_utc','expires_utc','bindings','limits','evidence'])
    require(record['schema_version']=='qwen-execution-grant-v1' and record['purpose']=='four_request_benign_readiness'
            and record['traffic_kind'] in {'mock','real'} and record['execution_authorized'] is True,'grant_scope_invalid')
    require(record['traffic_kind']==manifest['traffic_kind'],'grant_mock_real_mismatch')
    require(record['limits']==limits(),'grant_limits_mismatch')
    require(type(record['grant_id']) is str and re.fullmatch(r'[A-Za-z0-9_.:-]{1,96}',record['grant_id']) is not None,'grant_id_invalid')
    _exact(record['evidence'],['operator_authorization','model_license','source_authorization','privacy_review'])
    require(evidence_root is not None,'approval_evidence_required')
    for sha in record['evidence'].values():
        require(type(sha) is str and re.fullmatch(r'[a-f0-9]{64}',sha) is not None,'evidence_hash_invalid')
        p=Path(evidence_root)/(sha+'.private');require(p.is_file() and not p.is_symlink(),'approval_evidence_missing')
        require(p.stat().st_size<=65536 and digest(p.read_bytes())==sha,'approval_evidence_mismatch')
    validate_manifest_plan(manifest,plan)
    if record['traffic_kind']=='real':
        checkout=checkout_status()
        require(checkout['branch']=='experiment/stream-prada-order' and checkout['clean'] and checkout['main_unchanged']
                and manifest['collector_revision']==checkout['head'],'clean_pinned_experiment_checkout_required')
    require(record['evidence']['operator_authorization']==manifest['authorization']['evidence_sha256'],'manifest_approval_mismatch')
    grant=Grant(record,expected_sha256);grant.check(manifest,plan,now)
    return grant


def grant_registry():return HERE.parent/'traffic_local'/'execution_grants'


def grant_claimed(grant):return (grant_registry()/(grant.sha+'.claim.private')).exists()


def claim_grant(grant,storage_root,*,registry=None,worker_start=False):
    """One-shot checkout-local ledger, preserved even if boot never reaches inference.

    Copying an approval to a different folder does not reset its claim. Real mode
    cannot override the registry. ACL protection/operator review remain required.
    """
    from ..traffic_collection.store import _check_ignored_paths
    if registry is not None:require(grant.record['traffic_kind']=='mock','real_registry_override_forbidden')
    folder=Path(registry) if registry is not None else grant_registry()
    body={'schema_version':'qwen-grant-claim-v1','grant_sha256':grant.sha,
          'storage_path_sha256':digest(str(Path(storage_root).resolve())),
          'bindings':grant.record['bindings']}
    if worker_start:
        existing=read_json(folder/(grant.sha+'.claim.private'))
        require(existing==body,'grant_claim_owner_mismatch')
    path=folder/(grant.sha+('.worker.private' if worker_start else '.claim.private'))
    _check_ignored_paths(folder,[path.name]);folder.mkdir(parents=True,exist_ok=True)
    try:
        with path.open('xb') as f:f.write(canonical(body).encode());f.flush();os.fsync(f.fileno())
    except FileExistsError:require(False,'grant_already_claimed')
    return body
