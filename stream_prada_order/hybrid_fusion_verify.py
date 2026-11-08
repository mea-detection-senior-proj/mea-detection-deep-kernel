"""Bounded numeric-only verification. Never evaluates real detector traffic."""
import argparse
from datetime import datetime,timezone
import hashlib
import importlib.abc
import io
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))


def write_new(path,value):
    with path.open('x',encoding='utf-8',newline='\n') as f:json.dump(value,f,indent=2);f.write('\n')


def hashes(paths):return {p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}


def worker(output):
    assert sys.stdin.readline().strip()=='BOOT'
    class NoModelImports(importlib.abc.MetaPathFinder):
        def find_spec(self,fullname,path=None,target=None):
            if fullname.split('.')[0] in {'torch','transformers','sentence_transformers','numpy'}:
                raise ImportError('model_or_array_runtime_forbidden_in_numeric_fusion_tests')
    sys.meta_path.insert(0,NoModelImports())
    def offline(*a,**k):raise RuntimeError('network_forbidden')
    socket.socket.connect=offline;socket.socket.connect_ex=offline;socket.create_connection=offline
    os.environ.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',CUDA_VISIBLE_DEVICES='')
    suite=unittest.defaultTestLoader.loadTestsFromName('stream_prada_order.tests.test_hybrid_fusion')
    log=io.StringIO();started=time.monotonic();result=unittest.TextTestRunner(stream=log,verbosity=2).run(suite)
    record={'status':'passed' if result.wasSuccessful() else 'failed','tests_run':result.testsRun,
            'failures':len(result.failures),'errors':len(result.errors),'skipped':len(result.skipped),
            'seconds':time.monotonic()-started,'log':log.getvalue(),
            'imported_model_or_array_modules':[m for m in ['torch','transformers','sentence_transformers','numpy'] if m in sys.modules],
            'scope':'Synthetic numeric score fixtures only; no detector/model/data execution or performance estimate.'}
    write_new(output/'tests.json',record)
    return 0 if result.wasSuccessful() else 2


def verify(output):
    import psutil
    from stream_prada_order.traffic_runtime.winjob import WindowsJob
    def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT).decode().strip()
    assert git('branch','--show-current')=='experiment/stream-prada-order'
    assert git('rev-parse','main')=='5fb5e07d750a73a0a663a174433bab931ae7568a'
    assert not git('diff','HEAD','--name-only'),'Prior tracked bytes changed'
    assert not output.exists(),'New-only verification output required'
    output.mkdir(parents=True)
    paths=[ROOT/p for p in ['stream_prada_order/hybrid_fusion.py','stream_prada_order/tests/test_hybrid_fusion.py',
        'stream_prada_order/hybrid_fusion_config_v1.json','stream_prada_order/hybrid_fusion_verify.py',
        'stream_prada_order/HYBRID_FUSION_DESIGN_TH.md','stream_prada_order/HYBRID_MMD_CONTRACT_TH.md',
        'pilot/README.md','pilot/deep_kernel_pilot.py','stream_prada_order/PHASE_D_REPORT_TH.md',
        'stream_prada_order/PHASE_E_REPORT_TH.md','stream_prada_order/PHASE_F_PROTOCOL_TH.md']]
    before=hashes(paths)
    write_new(output/'preflight.json',{'observed_utc':datetime.now(timezone.utc).isoformat(),
        'branch':git('branch','--show-current'),'base_head':git('rev-parse','HEAD'),'source_hashes':before,
        'wall_gate_seconds':120,'worker_committed_cap_bytes':512*1024**2,'scientific_execution':False})
    job=WindowsJob(512*1024**2);p=None;start=time.monotonic();peak=0;failure=None
    try:
        p=subprocess.Popen([sys.executable,str(Path(__file__).resolve()),'--worker','--output',str(output)],
                           cwd=ROOT,stdin=subprocess.PIPE,creationflags=0x08000000)
        job.assign(p.pid);p.stdin.write(b'BOOT\n');p.stdin.flush();p.stdin.close()
        while p.poll() is None:
            try:peak=max(peak,psutil.Process(p.pid).memory_info().peak_wset)
            except psutil.NoSuchProcess:pass
            if time.monotonic()-start>=120 or peak>512*1024**2:
                failure='resource_gate';job.terminate();p.kill();break
            time.sleep(.01)
        p.wait(timeout=5);elapsed=time.monotonic()-start
        if elapsed>=120:failure='wall_gate'
        unchanged=before==hashes(paths) and not git('diff','HEAD','--name-only')
        record={'status':'passed' if p.returncode==0 and failure is None and unchanged else 'stopped',
                'exit_code':p.returncode,'seconds':elapsed,'observed_peak_working_set_bytes':peak,
                'worker_committed_cap_bytes':512*1024**2,'gate_failure':failure,
                'sources_unchanged':unchanged,'branch':git('branch','--show-current'),
                'main_unchanged':git('rev-parse','main')=='5fb5e07d750a73a0a663a174433bab931ae7568a',
                'model_loads':0,'detector_executions':0,'real_score_sessions_evaluated':0,
                'scientific_fpr':None,'scientific_tpr':None,'scientific_detection_delay':None}
        write_new(output/'verification.json',record);print(json.dumps(record));assert record['status']=='passed'
    finally:
        job.terminate()
        if p and p.poll() is None:p.kill();p.wait(timeout=5)
        job.close()


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);p.add_argument('--worker',action='store_true')
    args=p.parse_args();output=args.output.resolve()
    return worker(output) if args.worker else verify(output)

if __name__=='__main__':raise SystemExit(main())
