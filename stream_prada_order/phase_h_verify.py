"""Phase H offline verification: mock inference only, preserved Phase A-G sources."""
import argparse
from collections import Counter
import hashlib
import io
import json
import os
from pathlib import Path
import platform
import sqlite3
import subprocess
import sys
import time
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1];HERE=ROOT/'stream_prada_order'
sys.path.insert(0,str(ROOT))


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def write(path,value):path.write_bytes((json.dumps(value,indent=2,ensure_ascii=True,allow_nan=False)+'\n').encode())
def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT).decode().strip()


def worker():
    import socket
    def no_network(*_,**__):raise RuntimeError('offline_test_network_disabled')
    socket.socket.connect=no_network;socket.socket.connect_ex=no_network;socket.create_connection=no_network
    from stream_prada_order.traffic_runtime.backend import QwenBackend
    started=time.perf_counter();suite=unittest.defaultTestLoader.discover(str(HERE/'tests'))
    def ids(node):
        for item in node:
            if isinstance(item,unittest.TestSuite):yield from ids(item)
            else:yield item.id()
    names=list(ids(suite));output=io.StringIO()
    with patch.object(QwenBackend,'_load_native',side_effect=AssertionError('native_load_forbidden_in_phase_h')) as native:
        result=unittest.TextTestRunner(stream=output,verbosity=2).run(suite)
    import psutil
    peak=getattr(psutil.Process().memory_info(),'peak_wset',None)
    record={'status':'passed' if result.wasSuccessful() else 'failed','tests_run':result.testsRun,
            'failures':len(result.failures),'errors':len(result.errors),'skipped':len(result.skipped),
            'seconds':time.perf_counter()-started,'tests_by_module':dict(Counter(n.split('.')[0] for n in names)),
            'test_ids':names,'failed_test_ids':[t.id() for t,_ in result.failures+result.errors],
            'process_peak_working_set_bytes':peak,'native_backend_load_entries':native.call_count,
            'cuda_visible_devices':os.environ.get('CUDA_VISIBLE_DEVICES'),
            'real_worker_forbidden_in_children':os.environ.get('PHASE_H_OFFLINE_VERIFICATION')=='1',
            'outbound_socket_connect_guard':True,'fixture_scope':'Numeric mocks + legacy CPU numeric regression fixtures only.'}
    print(json.dumps(record))
    if not result.wasSuccessful():print(output.getvalue(),file=sys.stderr)
    return 0 if result.wasSuccessful() else 1


def verify(output):
    assert not output.exists(),'use_new_receipt_directory'
    assert git('branch','--show-current')=='experiment/stream-prada-order'
    assert not git('diff','--name-only')
    tracked=git('ls-files').splitlines();baseline={p:sha(ROOT/p) for p in tracked if (ROOT/p).is_file()}
    g_manifest=json.loads((HERE/'PHASE_G_MANIFEST.json').read_bytes())
    assert all(sha(ROOT/p)==v['sha256'] for p,v in g_manifest['files'].items()),'phase_g_frozen_artifact_changed'
    sources=[Path(__file__),*sorted((HERE/'traffic_runtime').glob('*.py')),
             *sorted((HERE/'traffic_runtime').glob('*.json')),*sorted((HERE/'tests').glob('*phase_h*.py'))]
    frozen={p.relative_to(ROOT).as_posix():sha(p) for p in sources}
    output.mkdir(parents=True)
    pre={'gate_seconds':120,'worker_memory_review_limit_bytes':2*1024**3,'cpu_only':True,
         'python':platform.python_version(),'sqlite':sqlite3.sqlite_version,'base_head':git('rev-parse','HEAD'),
         'main_sha':git('rev-parse','main'),'frozen_sources':frozen,
         'approved_real_requests':0,'approved_model_loads':0,'approved_weight_downloads':0}
    write(output/'preflight.json',pre)
    env=dict(os.environ,CUDA_VISIBLE_DEVICES='',HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',
             PHASE_H_OFFLINE_VERIFICATION='1',PYTHONIOENCODING='utf-8')
    try:
        child=subprocess.run([sys.executable,str(Path(__file__).resolve()),'--worker'],cwd=ROOT,env=env,
                              capture_output=True,text=True,encoding='utf-8',timeout=120)
    except subprocess.TimeoutExpired:
        write(output/'test_results.json',{'status':'blocked_timeout','gate_seconds':120});raise
    try:record=json.loads(child.stdout)
    except json.JSONDecodeError:
        write(output/'test_results.json',{'status':'failed_worker_protocol','exit_code':child.returncode});raise
    write(output/'test_results.json',record)
    if child.returncode:print(child.stderr,file=sys.stderr)
    assert child.returncode==0 and record['status']=='passed' and record['native_backend_load_entries']==0
    assert record['process_peak_working_set_bytes'] is None or record['process_peak_working_set_bytes']<=2*1024**3
    summary={'status':'passed','tests_run':record['tests_run'],'new_phase_h_tests':sum(v for k,v in record['tests_by_module'].items() if k.startswith('test_phase_h')),
             'prior_phase_a_g_tests':sum(v for k,v in record['tests_by_module'].items() if not k.startswith('test_phase_h')),
             'runtime_seconds':record['seconds'],'real_victim_requests':0,'model_weights_loaded':0,
             'model_weights_downloaded':0,'extraction_runs':0,'student_training_runs':0,'participant_records_collected':0,
             'native_runtime_compatibility':'unverified_no_actual_execution',
             'prior_tracked_files_unchanged':all(sha(ROOT/p)==h for p,h in baseline.items()),
             'frozen_sources_unchanged':all(sha(ROOT/p)==h for p,h in frozen.items()),
             'main_unchanged':git('rev-parse','main')==pre['main_sha'],'pushed':False}
    write(output/'verification.json',summary)
    write(output/'artifact_hashes.json',{p.name:sha(p) for p in sorted(output.iterdir()) if p.is_file() and p.name!='artifact_hashes.json'})
    assert summary['prior_tracked_files_unchanged'] and summary['frozen_sources_unchanged'] and summary['main_unchanged']
    print(json.dumps(summary,indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--worker',action='store_true');parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    if args.worker:raise SystemExit(worker())
    if not args.output:parser.error('--output required')
    verify(args.output)
