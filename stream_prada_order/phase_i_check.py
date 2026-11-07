"""Phase I offline checks; no acquisition, model construction or inference path.

Run from the repository root in senior; output must be a NEW ignored directory.
"""
import argparse
from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import time
from urllib.parse import quote

ROOT=Path.cwd().resolve()
sys.path.insert(0,str(ROOT))
H_REVISION='8d32d46bb1496862ddf36017b7eea811c01dc51c'
MODEL_REVISION='989aa7980e4cf806f80c7fef2b1adb7bc71aa306'
CACHE_KEYS=['HF_HOME','HF_HUB_CACHE','HUGGINGFACE_HUB_CACHE','XDG_CACHE_HOME',
            'TRANSFORMERS_CACHE','PYTORCH_TRANSFORMERS_CACHE','PYTORCH_PRETRAINED_BERT_CACHE']


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def utc():return datetime.now(timezone.utc).isoformat()
def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT,timeout=10).decode().strip()


def verify_frozen():
    from stream_prada_order.traffic_runtime.policy import code_digest
    result={}
    for phase in ['G','H']:
        name=f'stream_prada_order/PHASE_{phase}_MANIFEST.json';path=ROOT/name
        original=subprocess.check_output(['git','show',H_REVISION+':'+name],cwd=ROOT)
        if path.read_bytes()!=original:raise ValueError('historical_manifest_changed')
        manifest=json.loads(original)
        if not all(sha(ROOT/p)==v['sha256'] for p,v in manifest['files'].items()):
            raise ValueError('frozen_source_changed')
        result[phase]={'manifest_sha256':sha(path),'files_verified':len(manifest['files'])}
    return {'status':'passed','frozen_h_commit':H_REVISION,'manifests':result,'runtime_code_sha256':code_digest()}


def cache_roots(env,home):
    """Match installed Hub precedence, also inspect explicitly set legacy paths."""
    def expand(p):return os.path.expandvars(str(p).replace('~',str(home),1) if str(p).startswith('~') else str(p))
    hfhome=expand(env.get('HF_HOME') or Path(env.get('XDG_CACHE_HOME') or Path(home)/'.cache')/'huggingface')
    effective=env.get('HF_HUB_CACHE') or env.get('HUGGINGFACE_HUB_CACHE') or str(Path(hfhome)/'hub')
    values=[('effective_hub_cache',expand(effective))]
    for key in ['HF_HUB_CACHE','HUGGINGFACE_HUB_CACHE','TRANSFORMERS_CACHE','PYTORCH_TRANSFORMERS_CACHE','PYTORCH_PRETRAINED_BERT_CACHE']:
        if env.get(key):values.append((key,expand(env[key])))
    # Preserve H's default interpretation explicitly; it ignores XDG/legacy Hub vars.
    hhome=expand(env.get('HF_HOME') or Path(home)/'.cache/huggingface')
    values.append(('frozen_h_default',expand(env.get('HF_HUB_CACHE') or Path(hhome)/'hub')))
    result=[];seen=set()
    for origin,value in values:
        if value.startswith(('\\\\','//')):raise ValueError('network_cache_not_authorized')
        identity=os.path.normcase(os.path.abspath(value))
        if identity not in seen:result.append({'origin':origin,'path':identity});seen.add(identity)
    return result


def inventory(roots,locations=()):
    from stream_prada_order.traffic_runtime.readiness import inspect_snapshot
    candidates=[]
    for item in roots:
        cache=Path(item['path']);model=cache/'models--Qwen--Qwen2.5-1.5B-Instruct'
        candidates.append({'origin':item['origin'],'cache':str(cache),'model_dir_exists':model.is_dir(),
                           'snapshot':str(model/'snapshots'/MODEL_REVISION)})
    candidates.extend({'origin':'user_explicit_model_location','snapshot':str(p)} for p in locations)
    if len(candidates)>16:raise ValueError('candidate_root_budget_exceeded')
    started=time.monotonic();read=0;seen=set();reports=[]
    for item in candidates:
        raw=item['snapshot']
        if str(raw).startswith(('\\\\','//')):raise ValueError('network_model_location_not_authorized')
        path=Path(raw).expanduser().resolve();key=os.path.normcase(str(path))
        if key in seen:continue
        seen.add(key)
        remaining=120-(time.monotonic()-started)
        if remaining<=0:raise ValueError('snapshot_inventory_timeout')
        result=inspect_snapshot(path,read_cap=8*1024**3-read,seconds=remaining)
        read+=result['bytes_read']
        reports.append({**item,'snapshot':str(path),'verification':result})
    return {'schema_version':'phase-i-cache-inventory-v1','observed_utc':utc(),'candidates':reports,
            'bytes_read':read,'max_total_bytes':8*1024**3,'seconds':time.monotonic()-started,
            'all_required_hashes_verified':any(r['verification']['status']=='passed' for r in reports),
            'scope':'Only explicitly configured cache/model paths; no filesystem crawl or private logs.'}


def download_plan(lock):
    base='https://huggingface.co/'+lock['model_id']+'/resolve/'+lock['revision']+'/'
    files=[]
    for name,item in lock['files'].items():
        if Path(name).name!=name:raise ValueError('invalid_lock_filename')
        files.append({'name':name,'source_url':base+quote(name,safe=''),'bytes':item['bytes'],
                      'content_sha256':item['sha256'],'git_blob_sha1':item['git_blob_sha1']})
    total=sum(f['bytes'] for f in files)
    return {'schema_version':'phase-i-download-plan-v1','status':'PLAN_ONLY_SEPARATE_AUTHORIZATION_REQUIRED',
            'model_id':lock['model_id'],'revision':lock['revision'],'files':files,'required_file_count':len(files),
            'final_file_bytes':total,'staging_plus_final_conservative_bytes':2*total,
            'proposed_download_gate_seconds':1200,'proposed_logical_file_gets':len(files),'automatic_retries':0,
            'proposed_max_redirects_per_file':3,'proposed_max_http_transactions':4*len(files),
            'proposed_payload_plus_metadata_wire_cap_bytes':total+16*1024**2,
            'proposed_storage_cap_bytes':8*1024**3,'proposed_min_disk_free_bytes':9*1024**3,
            'proposed_destination_relative':'stream_prada_order/traffic_local/qwen_snapshots/'+lock['revision'],
            'license':'Apache-2.0; frozen upstream LICENSE plus human review required',
            'license_source':'https://huggingface.co/'+lock['model_id']+'/blob/'+lock['revision']+'/LICENSE',
            'license_file_sha256':sha(ROOT/'stream_prada_order/traffic_runtime/QWEN_LICENSE.txt'),
            'redirect_allowlist_status':'Must be reviewed/approved before transfer; no unreviewed host follow.',
            'source_availability_and_bandwidth':'unverified_no_network_requests',
            'no_download_performed':True,'no_download_function_or_cli_in_this_script':True}


def import_worker():
    os.environ.update(CUDA_VISIBLE_DEVICES='',HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',HF_HUB_DISABLE_TELEMETRY='1')
    def blocked(*_,**__):raise RuntimeError('network_disabled_for_import_probe')
    socket.socket.connect=blocked;socket.socket.connect_ex=blocked;socket.create_connection=blocked
    import psutil
    stage='torch'
    try:
        import torch
        stage='qwen_runtime_classes'
        from transformers import AutoTokenizer,Qwen2ForCausalLM,GenerationConfig
        stage='dependency_imports'
        import tokenizers,safetensors,jinja2
        result={'status':'passed_import_only','torch_version':torch.__version__,'torch_build_cuda':torch.version.cuda,
                'cuda_initialized':torch.cuda.is_initialized(),'qwen_class_imported':Qwen2ForCausalLM.__name__,
                'model_or_tokenizer_constructed':False,'weights_loaded':0,'victim_requests':0,'gpu_kernels_executed':0}
    except Exception as exc:result={'status':'blocked_import','stage':stage,'exception_type':type(exc).__name__}
    result['peak_working_set_bytes']=psutil.Process().memory_info().peak_wset
    print(json.dumps(result))


def cpu_import_probe():
    import psutil
    started=time.monotonic();peak=0;failure=None
    process=subprocess.Popen([sys.executable,str(Path(__file__).resolve()),'--import-worker'],cwd=ROOT,
                 stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,creationflags=0x08000000 if os.name=='nt' else 0)
    while process.poll() is None:
        try:peak=max(peak,psutil.Process(process.pid).memory_info().peak_wset)
        except psutil.NoSuchProcess:pass
        if time.monotonic()-started>45:failure='timeout_45_seconds'
        if peak>1024**3:failure='ram_cap_1gib'
        if failure:process.kill();break
        time.sleep(.02)
    stdout,_=process.communicate(timeout=5)
    try:result=json.loads(stdout) if not failure else {'status':'blocked_resource_gate'}
    except json.JSONDecodeError:result={'status':'blocked_protocol','exception_text_suppressed':True}
    peak=max(peak,result.get('peak_working_set_bytes',0))
    if peak>1024**3:failure='ram_cap_1gib'
    return {'scope':'CPU import-only; no model/tokenizer construction, weights or CUDA kernels',
            'observed_utc':utc(),'gate_seconds':45,'ram_cap_bytes':1024**3,'seconds':time.monotonic()-started,
            'observed_peak_bytes':peak,'exit_code':process.returncode,'gate_failure':failure,'result':result}


def disk_info(path):
    path=Path(path)
    while not path.exists():path=path.parent
    usage=shutil.disk_usage(path)
    return {'existing_ancestor':str(path),'free_bytes':usage.free,'total_bytes':usage.total}


def run(output,locations=(),extra_roots=()):
    from stream_prada_order.traffic_collection.store import _check_ignored_paths
    from stream_prada_order.traffic_runtime.policy import checkout_status,snapshot_lock
    from stream_prada_order.traffic_runtime.readiness import readiness
    checkout=checkout_status()
    if checkout['branch']!='experiment/stream-prada-order' or not checkout['clean'] or not checkout['main_unchanged']:
        raise ValueError('clean_isolated_checkout_required')
    if output.exists():raise ValueError('new_output_directory_required')
    names=['entry.json','clean_h_readiness.json','cache_inventory.json','download_plan.json',
           'cpu_import_probe.json','pip_check.json','storage_metadata.json','summary.json','artifact_hashes.json']
    _check_ignored_paths(output,names)
    output.mkdir(parents=True)
    def write(name,value):(output/name).write_bytes((json.dumps(value,indent=2,ensure_ascii=True,allow_nan=False)+'\n').encode())
    frozen=verify_frozen()
    write('entry.json',{'schema_version':'phase-i-entry-v1','observed_utc':utc(),'checkout':checkout,'frozen':frozen,
                        'checker_source_sha256':sha(Path(__file__))})
    check=readiness();check['observed_utc']=utc()
    check['model_runtime_modules_imported']=[n for n in ['torch','transformers','tokenizers','safetensors'] if n in sys.modules]
    write('clean_h_readiness.json',check)
    env={key:os.environ.get(key) for key in CACHE_KEYS}
    roots=cache_roots(env,Path.home())+list(extra_roots)
    for item in roots:
        if str(item['path']).startswith(('\\\\','//')):raise ValueError('network_cache_not_authorized')
    inspected=inventory(roots,locations)
    write('cache_inventory.json',{'allowlisted_environment':env,'user_provided_locations':[str(p) for p in locations],**inspected})
    plan=download_plan(snapshot_lock());write('download_plan.json',plan)
    proposed=ROOT/plan['proposed_destination_relative']
    write('storage_metadata.json',{'workspace':disk_info(ROOT),'cache_volumes':[disk_info(r['path']) for r in roots],
           'proposed_destination':str(proposed),'proposed_destination_volume':disk_info(proposed),
           'pilot_store_created':False,'acl_or_privacy_approval_created':False,'grant_created_or_claimed':False})
    write('cpu_import_probe.json',probe:=cpu_import_probe())
    try:
        process=subprocess.run([sys.executable,'-m','pip','check'],capture_output=True,text=True,timeout=20,cwd=ROOT)
        pip={'exit_code':process.returncode,'stdout':process.stdout[:16384],'stderr_suppressed':bool(process.stderr),
             'seconds_gate':20,'network_requests':0}
    except subprocess.TimeoutExpired:pip={'status':'blocked_timeout','seconds_gate':20}
    write('pip_check.json',pip)
    after=checkout_status()
    if after!=checkout:raise ValueError('checkout_changed_during_checks')
    if verify_frozen()!=frozen:raise ValueError('frozen_sources_changed_during_checks')
    summary={'status':'NO-GO_REAL_PILOT','snapshot_hashes_verified':inspected['all_required_hashes_verified'],
             'clean_h_readiness_codes':check['codes'],'cpu_import_result':probe['result']['status'],
             'cpu_import_gate_failure':probe['gate_failure'],'pip_check_exit_code':pip.get('exit_code'),
             'runtime_gpu_kernel_bf16_model_load_generation':'unverified',
             'weights_downloaded':0,'weights_loaded':0,'gpu_kernels_executed':0,'victim_requests':0,
             'attacks':0,'student_training':0,'participant_records':0,'approval_grants_created_or_claimed':0,
             'checkout_remained_clean':True,'historical_frozen_sources_unchanged':True}
    write('summary.json',summary)
    write('artifact_hashes.json',{name:sha(output/name) for name in names if name!='artifact_hashes.json'})
    print(json.dumps(summary,indent=2))


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--import-worker',action='store_true')
    parser.add_argument('--output',type=Path);parser.add_argument('--model-location',type=Path,action='append',default=[])
    parser.add_argument('--cache-root',type=Path,action='append',default=[]);args=parser.parse_args()
    if args.import_worker:return import_worker()
    if args.output is None:parser.error('--output required')
    try:return run(args.output,args.model_location,[{'origin':'user_explicit_cache','path':str(p)} for p in args.cache_root])
    except Exception as exc:
        print(json.dumps({'status':'BLOCKED_OFFLINE_CHECK','exception_type':type(exc).__name__,
                          'details_suppressed':True,'model_execution_enabled':False}))
        return 2


if __name__=='__main__':raise SystemExit(main())
