"""Contained worker IPC. Real branch is reachable only after revalidating grant."""
import json
import os
import socket
import time

from ..traffic_collection.schema import canonical, require, strict_json, IntegrityError
from .policy import load_grant, limits

MAX_FRAME=262144
SAFE_ERROR_CODES={'out_of_memory','environment_import_failed','local_runtime_io_failed',
                  'boot_failed','prepare_failed','generation_failed','input_token_cap_exceeded',
                  'output_byte_cap_exceeded','gpu_reserved_cap_exceeded','cuda_bf16_unavailable',
                  'bf16_kernel_probe_failed','chat_template_mismatch','worker_snapshot_invalid',
                  'worker_environment_invalid','worker_resources_invalid','generation_resource_or_integrity_guard'}


def classify(exc,phase):
    if type(exc).__name__ in {'OutOfMemoryError','MemoryError'}:return 'out_of_memory'
    if isinstance(exc,ImportError):return 'environment_import_failed'
    if isinstance(exc,OSError):return 'local_runtime_io_failed'
    if isinstance(exc,IntegrityError) and str(exc) in SAFE_ERROR_CODES:return str(exc)
    return {'boot':'boot_failed','prepare':'prepare_failed','generate':'generation_failed'}[phase]


def send(conn,value):
    raw=canonical(value).encode();require(len(raw)<=MAX_FRAME,'ipc_frame_too_large');conn.send_bytes(raw)


def receive(conn):
    return strict_json(conn.recv_bytes(MAX_FRAME))


def run_worker(conn,options):
    # Never run a model/import it before the parent has attached the OS job and sent boot.
    phase='boot'
    try:
        boot=receive(conn);require(boot=={'kind':'boot'},'worker_boot_required')
        if os.environ.get('PHASE_H_OFFLINE_VERIFICATION')=='1':
            require(options.get('mode')=='mock','real_worker_forbidden_during_verification')
        os.environ.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',HF_HUB_DISABLE_TELEMETRY='1',
                          HF_HUB_DISABLE_PROGRESS_BARS='1',TOKENIZERS_PARALLELISM='false')
        def no_network(*_,**__):raise RuntimeError('offline_runtime_network_disabled')
        socket.socket.connect=no_network;socket.socket.connect_ex=no_network;socket.create_connection=no_network
        mock=options['mode']=='mock'
        if mock:
            require(options.get('mock_marker')=='numeric-tests-only','invalid_mock_worker')
            if options.get('boot_hang'):time.sleep(60)
            if options.get('boot_failure'):raise MemoryError('numeric-fixture-only')
            backend=None
        else:
            require(options['mode']=='real' and options.get('execution_authorized') is True,'real_execution_not_authorized')
            grant=load_grant(options['approval'],options['approval_sha'],options['manifest'],options['plan'],options['evidence_root'])
            require(grant.record['traffic_kind']=='real','real_grant_required')
            from .readiness import inspect_snapshot, environment, resource_codes, resource_snapshot
            require(inspect_snapshot(options['snapshot'])['status']=='passed','worker_snapshot_invalid')
            require(environment()['status']=='passed_static_only','worker_environment_invalid')
            require(not resource_codes(resource_snapshot(options['storage_root'])),'worker_resources_invalid')
            from .backend import QwenBackend
            backend=QwenBackend();backend.load(options['snapshot'],execution_authorized=True,grant=grant,
                                              manifest=options['manifest'],plan=options['plan'])
        send(conn,{'kind':'ready','pid':os.getpid()})
        pending=None
        while True:
            command=receive(conn)
            if command=={'kind':'close'}:break
            if command.get('kind')=='prepare':
                phase='prepare'
                require(pending is None,'worker_pending_request')
                if mock:
                    if options.get('prepare_crash'):os._exit(73)
                    ids=list(options.get('input_ids',[1,2,3]))
                    prepared={'rendered_prompt':'1 2 3','rendered_prompt_sha256':__import__('hashlib').sha256(b'1 2 3').hexdigest(),
                              'input_ids':ids,'input_tokens':len(ids),'chat_template_sha256':options['template_sha256']}
                else:prepared=backend.prepare(command['query'])
                require(prepared['input_tokens']<=limits()['max_input_tokens'],'input_token_cap_exceeded')
                pending=prepared;send(conn,{'kind':'prepared',**prepared})
            elif command.get('kind')=='generate':
                phase='generate'
                require(pending is not None,'worker_prepare_required')
                send(conn,{'kind':'accepted'})
                try:
                    if mock:
                        if options.get('generate_crash'):os._exit(73)
                        if options.get('generate_hang'):time.sleep(60)
                        if options.get('generate_failure'):raise RuntimeError('numeric-fixture-error')
                        output={'text':'4 5','input_tokens':pending['input_tokens'],'output_tokens':2,'output_ids':[4,5],
                                'gpu_peak_reserved_bytes':0}
                    else:output=backend.generate()
                    send(conn,{'kind':'result',**output});pending=None
                except Exception as exc:
                    code=classify(exc,'generate')
                    send(conn,{'kind':'error','code':code,'delivery':'accepted'});break
            else:require(False,'worker_protocol_invalid')
    except BaseException as exc:
        try:send(conn,{'kind':'error','code':classify(exc,phase),'delivery':'unknown' if phase=='generate' else 'not_sent'})
        except Exception:pass
    finally:conn.close()
