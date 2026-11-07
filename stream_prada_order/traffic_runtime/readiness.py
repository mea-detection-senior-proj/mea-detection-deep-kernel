"""Offline bounded byte/hash + static environment inspection; never imports a model."""
import ast
import hashlib
import importlib.metadata
import os
from pathlib import Path
import platform
import shutil
import subprocess
import time

from ..traffic_collection.schema import require, IntegrityError, canonical, digest
from .policy import profile, snapshot_lock, environment_lock, limits, load_grant, grant_claimed, checkout_status


def default_snapshot():
    hub=Path(os.environ.get('HF_HUB_CACHE',Path(os.environ.get('HF_HOME',Path.home()/'.cache/huggingface'))/'hub'))
    return hub/'models--Qwen--Qwen2.5-1.5B-Instruct'/'snapshots'/profile()['identity']['model_revision']


def inspect_snapshot(snapshot,lock=None,read_cap=8*1024**3,seconds=120):
    lock=lock or snapshot_lock();snapshot=Path(snapshot);started=time.monotonic();read=0;verified=[];errors=[]
    if not snapshot.is_dir():return {'status':'blocked','codes':['snapshot_missing'],'bytes_read':0,'verified_files':[]}
    expected=set(lock['files']);extras={p.name for p in snapshot.iterdir()}-expected-{'README.md','.gitattributes'}
    if extras:errors.append('snapshot_unreviewed_extra_files')
    for name,item in lock['files'].items():
        require(Path(name).name==name,'snapshot_lock_path_invalid')
        p=snapshot/name
        if not p.is_file():errors.append('snapshot_required_file_missing');continue
        if p.is_symlink():
            # Standard HF links may resolve only inside this repository's blobs directory.
            allowed=snapshot.parent.parent/'blobs'
            if not p.resolve().is_relative_to(allowed.resolve()):errors.append('snapshot_link_outside_blobs');continue
        if p.stat().st_size!=item['bytes']:errors.append('snapshot_size_mismatch');continue
        if read+item['bytes']>read_cap:errors.append('snapshot_read_budget_exceeded');break
        h=hashlib.sha256() if item['sha256'] else hashlib.sha1()
        if not item['sha256']:h.update(b'blob '+str(item['bytes']).encode()+b'\0')
        with p.open('rb') as f:
            while True:
                if time.monotonic()-started>seconds:errors.append('snapshot_hash_timeout');break
                raw=f.read(1024*1024)
                if not raw:break
                read+=len(raw)
                if read>read_cap:errors.append('snapshot_read_budget_exceeded');break
                h.update(raw)
        if h.hexdigest()!=(item['sha256'] or item['git_blob_sha1']):errors.append('snapshot_hash_mismatch')
        else:verified.append(name)
        if time.monotonic()-started>seconds or read>read_cap:break
    return {'status':'passed' if not errors and len(verified)==len(expected) else 'blocked',
            'codes':sorted(set(errors)),'bytes_read':read,'verified_files':verified,
            'hash_authority':'pinned Phase F Git blob identities / LFS SHA256; not self-certified local hashes',
            'model_or_tokenizer_loaded':False}


def environment():
    lock=environment_lock();versions={};issues=[];api={}
    for name,expected in lock['packages'].items():
        try:versions[name]=importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:versions[name]=None
        if versions[name]!=expected:issues.append('package_version_mismatch:'+name)
    if platform.python_version()!=lock['python']:issues.append('python_version_mismatch')
    if platform.system()!=lock['system']:issues.append('windows_runtime_required')
    try:
        base=Path(importlib.metadata.distribution('transformers').locate_file('transformers'))
        checks={'qwen2_class':('models/qwen2/modeling_qwen2.py','Qwen2ForCausalLM'),
                'chat_template':('tokenization_utils_base.py','apply_chat_template'),
                'generate':('generation/utils.py','generate')}
        for key,(name,symbol) in checks.items():
            tree=ast.parse((base/name).read_text(encoding='utf-8'))
            api[key]=any(isinstance(node,(ast.ClassDef,ast.FunctionDef)) and node.name==symbol for node in ast.walk(tree))
        if not all(api.values()):issues.append('static_api_missing')
    except Exception:issues.append('static_api_unavailable')
    return {'status':'passed_static_only' if not issues else 'blocked','codes':issues,'python':platform.python_version(),
            'system':platform.system(),'packages':versions,'static_api_symbols':api,
            'imports_kernel_bf16_generation_compatibility':'unverified_no_execution',
            'torch_or_transformers_imported_by_check':False}


def resource_snapshot(storage_root=None):
    import psutil  # OS metadata only; no CUDA/model imports.
    path=Path(storage_root) if storage_root else Path.cwd()
    while not path.exists():path=path.parent
    result={'available_ram_bytes':psutil.virtual_memory().available,'disk_free_bytes':shutil.disk_usage(path).free,
            'gpu_free_bytes':None,'gpu_name':None,'driver':None}
    try:
        raw=subprocess.check_output(['nvidia-smi','--query-gpu=index,name,driver_version,memory.free',
                                     '--format=csv,noheader,nounits'],timeout=3,creationflags=0x08000000 if os.name=='nt' else 0)
        row=raw.decode().strip().splitlines()[0].split(',')
        require(row[0].strip()=='0','gpu0_missing')
        result.update(gpu_free_bytes=int(row[-1].strip())*1024**2,gpu_name=row[1].strip(),driver=row[2].strip())
    except Exception:pass
    return result


def resource_codes(snapshot,running=False):
    l=limits();codes=[]
    for field,minimum in [('available_ram_bytes',l['min_available_ram_bytes']),('disk_free_bytes',l['min_disk_free_bytes']),
                          ('gpu_free_bytes',l['min_running_gpu_free_bytes'] if running else l['min_gpu_free_bytes'])]:
        if type(snapshot.get(field)) is not int or snapshot[field]<minimum:codes.append(field+'_gate_failed')
    if snapshot.get('gpu_name')!=environment_lock()['reviewed_gpu'] or snapshot.get('driver')!=environment_lock()['reviewed_driver']:
        codes.append('gpu_driver_review_mismatch')
    return codes


def readiness(snapshot=None,approval=None,approval_sha=None,manifest=None,plan=None,evidence_root=None,storage_root=None):
    snap=inspect_snapshot(snapshot or default_snapshot());env=environment();resources=resource_snapshot(storage_root)
    codes=[*snap['codes'],*env['codes'],*resource_codes(resources)]
    checkout=checkout_status()
    if checkout['branch']!='experiment/stream-prada-order' or not checkout['main_unchanged']:codes.append('branch_isolation_failed')
    if not checkout['clean']:codes.append('checkout_not_clean_rerun_after_commit')
    grant=None
    try:
        grant=load_grant(approval,approval_sha,manifest,plan,evidence_root)
        if grant_claimed(grant):codes.append('grant_already_claimed')
    except (IntegrityError,OSError,TypeError,KeyError,ValueError):codes.append('valid_explicit_approval_and_evidence_required')
    if not storage_root:codes.append('explicit_private_storage_required')
    else:
        try:
            from ..traffic_collection.store import check_private_root
            check_private_root(storage_root)
            if Path(storage_root).exists() and any(Path(storage_root).iterdir()):codes.append('fresh_pilot_store_required')
        except Exception:codes.append('private_storage_gate_failed')
    return {'schema_version':'qwen-offline-readiness-v1','status':'BLOCKED' if codes else 'STATIC_READY_RUNTIME_UNVERIFIED',
            'codes':sorted(set(codes)),'snapshot':snap,'environment':env,'resources':resources,
            'checkout':checkout,
            'approval_valid':grant is not None,'real_execution_enabled':False,
            'native_inference_verified':False,'victim_requests':0,'model_weights_loaded':0,
            'private_traffic_scanned':False,'static_checks_are_not_authorization_to_execute':True}
