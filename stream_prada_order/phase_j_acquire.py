"""Phase J pinned file acquisition. No model imports, inference, or automatic approval.

All production execution requires a hash-bound explicit operator approval record.
HTTP accounting covers response bodies + serialized headers, not TLS/TCP overhead.
"""
import argparse
from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import urllib.request
import urllib.error
from urllib.parse import urlsplit,urljoin

ROOT=Path.cwd().resolve();sys.path.insert(0,str(ROOT))


class Stop(RuntimeError):pass
def require(ok,code):
    if not ok:raise Stop(code)
def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False)
def digest(raw):return hashlib.sha256(raw).hexdigest()
def utc():return datetime.now(timezone.utc).isoformat()
def read_json(path):
    with Path(path).open('rb') as f:raw=f.read(1048577)
    require(len(raw)<=1048576,'metadata_size_cap');return json.loads(raw)
def write_new(path,value):
    raw=(json.dumps(value,indent=2,ensure_ascii=True,allow_nan=False)+'\n').encode()
    with Path(path).open('xb') as f:f.write(raw);f.flush();os.fsync(f.fileno())


def check_url(url,hosts):
    parsed=urlsplit(url)
    require(parsed.scheme=='https' and parsed.hostname in hosts and parsed.port in {None,443}
            and parsed.username is None and parsed.password is None and not parsed.fragment,'unapproved_url')


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):return None


def real_open(url,timeout):
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect())
    request=urllib.request.Request(url,headers={'User-Agent':'Deep-Kernel-Phase-J-acquisition',
                                               'Accept-Encoding':'identity'},method='GET')
    try:return opener.open(request,timeout=timeout)
    except urllib.error.HTTPError as exc:return exc


def tree_bytes(path):
    path=Path(path)
    if not path.exists():return 0
    total=0
    for item in path.rglob('*'):
        require(not item.is_symlink(),'symlink_storage_refused')
        if item.is_file():total+=item.stat().st_size
    return total


class Transfer:
    def __init__(self,plan,run_root,destination,*,open_request=None,clock=time.monotonic,disk_free=None):
        self.plan=plan;self.run_root=Path(run_root);self.destination=Path(destination)
        self.open_request=open_request or real_open;self.clock=clock
        self.disk_free=disk_free or (lambda:shutil.disk_usage(self.run_root).free)
        self.started=None;self.http_requests=0;self.logical_gets=0;self.body_bytes=0;self.header_bytes=0
        self.results=[];self.events=None

    def event(self,kind,**data):
        record={'utc':utc(),'kind':kind,'http_requests':self.http_requests,
                'logical_gets':self.logical_gets,'response_body_bytes':self.body_bytes,
                'serialized_header_bytes':self.header_bytes,**data}
        self.events.write(canonical(record)+'\n');self.events.flush();os.fsync(self.events.fileno())

    def guard(self,reserve=0):
        l=self.plan['limits']
        require(self.clock()-self.started<l['wall_seconds'],'wall_gate_failed')
        require(self.body_bytes+self.header_bytes+reserve<=l['http_accounted_bytes'],'http_byte_gate_failed')
        require(self.http_requests<=l['http_transactions'] and self.logical_gets<=l['logical_gets'],'request_gate_failed')
        require(tree_bytes(self.run_root)+tree_bytes(self.destination)+reserve<=l['storage_bytes'],'storage_gate_failed')
        require(self.disk_free()>=l['running_disk_reserve_bytes']+reserve,'disk_free_gate_failed')

    def fetch(self,spec,snapshot):
        self.logical_gets+=1;self.guard();url=spec['source_url']+'?download=true'
        response=None
        for hop in range(self.plan['limits']['redirects_per_file']+1):
            check_url(url,set(self.plan['allowed_https_hosts']))
            require(self.http_requests<self.plan['limits']['http_transactions'],'http_request_cap')
            self.http_requests+=1;self.guard()
            response=self.open_request(url,min(15,max(.1,self.plan['limits']['wall_seconds']-(self.clock()-self.started))))
            # urllib exposes parsed headers; this is explicit HTTP application accounting.
            self.header_bytes+=len(response.headers.as_bytes())+64
            self.guard()
            self.event('http_response',file=spec['name'],host=urlsplit(url).hostname,status=response.status,
                       url_sha256=digest(url.encode()))
            if response.status in {301,302,303,307,308}:
                location=response.headers.get('Location');response.close()
                require(location is not None and hop<self.plan['limits']['redirects_per_file'],'redirect_cap_or_missing_location')
                url=urljoin(url,location);continue
            break
        require(response is not None,'response_missing')
        try:
            require(response.status==200,'http_status_not_200')
            require(response.headers.get('Content-Encoding','identity').lower()=='identity','encoded_body_refused')
            length=response.headers.get('Content-Length')
            if length is not None:require(int(length)==spec['bytes'],'content_length_mismatch')
            require(not response.headers.get('Content-Range'),'partial_response_refused')
            sha=hashlib.sha256();git_hash=hashlib.sha1(b'blob '+str(spec['bytes']).encode()+b'\0');received=0
            partial=self.run_root/(spec['name']+'.partial')
            self.event('file_started',file=spec['name'],expected_bytes=spec['bytes'])
            last_progress=self.clock()
            with partial.open('xb') as f:
                while True:
                    self.guard(1024*1024)
                    chunk=response.read(min(1024*1024,spec['bytes']-received+1))
                    if not chunk:break
                    self.body_bytes+=len(chunk);received+=len(chunk)
                    self.guard(len(chunk))
                    require(received<=spec['bytes'],'body_oversized')
                    f.write(chunk);sha.update(chunk);git_hash.update(chunk)
                    if self.clock()-last_progress>=2:
                        self.event('file_progress',file=spec['name'],file_bytes=received)
                        print(json.dumps({'file':spec['name'],'bytes':received,'expected':spec['bytes']}),flush=True)
                        last_progress=self.clock()
                f.flush();os.fsync(f.fileno())
            require(received==spec['bytes'],'body_truncated')
            expected=spec['content_sha256'] or spec['git_blob_sha1']
            observed=sha.hexdigest() if spec['content_sha256'] else git_hash.hexdigest()
            require(observed==expected,'hash_mismatch')
            target=snapshot/spec['name'];require(not target.exists(),'staging_file_exists')
            # Both files remain within one controlled root; no overwrite and no copying.
            os.link(partial,target);partial.unlink()
            result={'file':spec['name'],'bytes':received,'sha256':sha.hexdigest(),'git_blob_sha1':git_hash.hexdigest(),
                    'expected_digest':expected,'verified_digest':observed,'verified':True}
            self.results.append(result);self.event('file_verified',**result)
        finally:response.close()

    def acquire(self,*,operator_authorized=False):
        require(operator_authorized is True,'operator_authorization_required')
        require(not self.run_root.exists() and not self.destination.exists(),'new_storage_paths_required')
        require(shutil.disk_usage(self.run_root.parent).free>=self.plan['limits']['initial_disk_free_bytes'],'initial_disk_gate_failed')
        self.started=self.clock();self.run_root.mkdir();snapshot=self.run_root/'snapshot'
        snapshot.mkdir();self.events=(self.run_root/'events.jsonl').open('x',encoding='utf-8',newline='\n')
        try:
            self.event('acquisition_started',plan_sha256=digest(canonical(self.plan).encode()))
            for spec in self.plan['files']:self.fetch(spec,snapshot)
            self.guard()
            require(set(p.name for p in snapshot.iterdir())=={s['name'] for s in self.plan['files']},'snapshot_file_set_mismatch')
            self.destination.parent.mkdir(parents=True,exist_ok=True)
            require(not self.destination.exists(),'destination_exists')
            # On Windows os.rename refuses an existing destination; never replace old evidence.
            require(os.name=='nt' or self.plan.get('numeric_fixture') is True,'windows_atomic_publish_required')
            os.rename(snapshot,self.destination)
            result={'status':'acquired_verified','seconds':self.clock()-self.started,'files':self.results,
                    'logical_gets':self.logical_gets,'http_transactions':self.http_requests,
                    'response_body_bytes':self.body_bytes,'serialized_header_bytes':self.header_bytes,
                    'http_accounted_bytes':self.body_bytes+self.header_bytes,
                    'http_accounting_scope':'response bodies + serialized response headers + conservative status allowance; TLS/TCP unmeasured',
                    'physical_storage_file_sizes':tree_bytes(self.run_root)+tree_bytes(self.destination),
                    'weights_loaded':0,'victim_requests':0,'model_or_tokenizer_imports':False}
            self.event('acquisition_completed',seconds=result['seconds'])
            write_new(self.run_root/'result.json',result)
            return result
        except BaseException as exc:
            code=str(exc) if isinstance(exc,Stop) else type(exc).__name__
            self.event('acquisition_stopped',code=code)
            write_new(self.run_root/'stopped.json',{'status':'stopped','code':code,'seconds':self.clock()-self.started,
                'body_bytes':self.body_bytes,'header_bytes':self.header_bytes,'http_requests':self.http_requests})
            raise
        finally:self.events.close()


def validate_plan(plan):
    from stream_prada_order.traffic_runtime.policy import snapshot_lock
    require(plan['schema_version']=='phase-j-acquisition-plan-v1','plan_version')
    old=read_json(ROOT/'stream_prada_order/diagnostics/phase_i_preflight_20261107_v2/download_plan.json')
    require(plan['files']==old['files'] and plan['revision']==old['revision'],'frozen_plan_changed')
    require(plan['allowed_https_hosts']==['huggingface.co','us.aws.cdn.hf.co'],'unreviewed_hosts')
    require(plan['snapshot_lock_sha256']==digest((ROOT/'stream_prada_order/traffic_runtime/snapshot_lock_v1.json').read_bytes()),'lock_changed')
    l=plan['limits']
    require(l=={'wall_seconds':1200,'logical_gets':8,'http_transactions':32,'redirects_per_file':3,
       'http_accounted_bytes':3115744227,'storage_bytes':8589934592,'initial_disk_free_bytes':9663676416,
       'running_disk_reserve_bytes':1073741824,'worker_memory_bytes':536870912,'retries':0},'limits_changed')
    destination=ROOT/old['proposed_destination_relative'];require(str(destination.resolve())==plan['destination'],'destination_changed')
    from stream_prada_order.traffic_collection.store import _check_ignored_paths
    for target in [destination,Path(plan['run_root'])]:
        require(target.resolve().is_relative_to((ROOT/'stream_prada_order/traffic_local').resolve()),'outside_ignored_workspace')
        for parent in [target,*target.parents]:
            require(not parent.is_symlink(),'symlink_parent_refused')
            if parent==ROOT:break
        _check_ignored_paths(target,[s['name'] for s in plan['files']]+[s['name']+'.partial' for s in plan['files']]+['events.jsonl','result.json','stopped.json'])
    require(snapshot_lock()['revision']==plan['revision'],'snapshot_revision_changed')


def validate_approval(plan,path,expected_sha):
    require(path is not None and expected_sha is not None,'operator_authorization_required')
    with Path(path).open('rb') as f:raw=f.read(65537)
    require(len(raw)<=65536 and digest(raw)==expected_sha,'approval_hash_mismatch')
    approval=json.loads(raw)
    require(approval.get('schema_version')=='phase-j-operator-approval-v1' and approval.get('approved') is True
            and approval.get('source')=='explicit_operator_chat_reply','explicit_operator_approval_required')
    require(approval.get('plan_sha256')==digest(canonical(plan).encode()),'approval_plan_mismatch')
    require(type(approval.get('operator_reply')) is str and bool(approval['operator_reply'].strip()),'operator_reply_missing')
    require(approval.get('acquisition_only') is True,'inference_not_authorized')
    require(plan['worker_source_sha256']==digest(Path(__file__).read_bytes()),'acquirer_source_changed')
    from stream_prada_order.traffic_runtime.policy import checkout_status
    checkout=checkout_status()
    require(checkout['branch']=='experiment/stream-prada-order' and checkout['clean'] and checkout['main_unchanged']
            and checkout['head']==plan['base_head'],'clean_frozen_checkout_required')


def worker(plan_path,approval_path,approval_sha):
    plan=read_json(plan_path);validate_plan(plan);validate_approval(plan,approval_path,approval_sha)
    return Transfer(plan,plan['run_root'],plan['destination']).acquire(operator_authorized=True)


def supervise(plan_path,approval_path,approval_sha):
    plan=read_json(plan_path);validate_plan(plan);validate_approval(plan,approval_path,approval_sha)
    require(os.name=='nt','windows_supervisor_required')
    from stream_prada_order.traffic_runtime.winjob import WindowsJob
    import psutil
    # Child waits on stdin until attached to job; no artifact request before containment.
    command=[sys.executable,str(Path(__file__).resolve()),'--worker','--plan',str(plan_path),
             '--approval',str(approval_path),'--approval-sha256',approval_sha]
    job=WindowsJob(plan['limits']['worker_memory_bytes']);p=None;started=time.monotonic();peak=0;failure=None
    try:
        p=subprocess.Popen(command,stdin=subprocess.PIPE,creationflags=0x08000000)
        job.assign(p.pid);p.stdin.write(b'BOOT\n');p.stdin.flush();p.stdin.close()
        while p.poll() is None:
            try:peak=max(peak,psutil.Process(p.pid).memory_info().peak_wset)
            except psutil.NoSuchProcess:pass
            if time.monotonic()-started>=1200:failure='external_wall_gate'
            if peak>plan['limits']['worker_memory_bytes']:failure='external_ram_gate'
            if failure:
                job.terminate()
                try:p.kill()
                except OSError:pass
                break
            time.sleep(.05)
        p.wait(timeout=5)
        elapsed=time.monotonic()-started
        if elapsed>=1200:failure='external_wall_gate'
        receipt={'status':'passed' if p.returncode==0 and failure is None else 'stopped',
                 'exit_code':p.returncode,'gate_failure':failure,'seconds':elapsed,
                 'observed_worker_peak_bytes':peak,'model_inference_executed':False}
        run=Path(plan['run_root'])
        if run.exists():write_new(run/'supervisor.json',receipt)
        require(receipt['status']=='passed','acquisition_worker_stopped')
        return receipt
    finally:
        job.terminate()
        if p and p.poll() is None:
            try:p.kill()
            except OSError:pass
            p.wait(timeout=5)
        job.close()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan',type=Path,required=True);parser.add_argument('--approval',type=Path)
    parser.add_argument('--approval-sha256');parser.add_argument('--worker',action='store_true');args=parser.parse_args()
    try:
        if args.worker:
            require(sys.stdin.buffer.readline(16)==b'BOOT\n','contained_boot_required')
            worker(args.plan,args.approval,args.approval_sha256)
        else:supervise(args.plan,args.approval,args.approval_sha256)
        return 0
    except Exception as exc:
        print(json.dumps({'status':'STOPPED','code':str(exc) if isinstance(exc,Stop) else type(exc).__name__,
                          'exception_details_suppressed':True,'inference_executed':False}),flush=True)
        return 2


if __name__=='__main__':raise SystemExit(main())
