"""External lifetime watchdog + contained worker; no thread-based inference timeout."""
import multiprocessing
import os
import threading
import time

from ..traffic_collection.adapters import AdapterFailure
from ..traffic_collection.schema import require, ExecutionDisabled, IntegrityError
from .policy import limits, profile, load_grant, claim_grant
from .worker import run_worker, send, receive, SAFE_ERROR_CODES
from .winjob import WindowsJob


class RuntimeFailure(AdapterFailure):
    def __init__(self,code,delivery='unknown'):
        super().__init__('timeout' if code=='wall_timeout' else 'adapter_failure',delivery,False)
        self.runtime_code=code


class Supervisor:
    def __init__(self,options,*,timeout=None,resource_check=None):
        self.options=dict(options);self.timeout=limits()['max_run_seconds'] if timeout is None else timeout
        require(0<self.timeout<=limits()['max_run_seconds'],'invalid_supervisor_deadline')
        self.resource_check=resource_check;self.proc=self.conn=self.job=None
        self.failure=None;self.done=threading.Event();self.lock=threading.RLock()
        self.watchdog=self.monitor=None;self.generation_dispatched=False
        self.deadline=None;self.input_total=self.output_total=self.requests=0;self.guard_codes=[]

    def _abort(self,code):
        with self.lock:
            if self.failure is None:self.failure=code
            if self.job:self.job.terminate()
            # Assignment may have failed: an empty job cannot terminate that child.
            if self.proc and self.proc.pid and self.proc.is_alive():
                try:self.proc.kill()
                except OSError:pass  # Job termination may have won the race.
            self.done.set()

    def _watch(self):
        if not self.done.wait(max(0,self.deadline-time.monotonic())):self._abort('wall_timeout')

    def _monitor(self):
        while not self.done.wait(0.05):
            try:
                codes=self.resource_check() if self.resource_check else []
                if codes:
                    allowed={'available_ram_bytes_gate_failed','disk_free_bytes_gate_failed','gpu_free_bytes_gate_failed','gpu_driver_review_mismatch','private_storage_guard_failed'}
                    self.guard_codes=[c for c in codes if c in allowed] or ['resource_guard_failed']
                    self._abort('resource_guard_failed');return
            except IntegrityError:
                self.guard_codes=['private_storage_guard_failed'];self._abort('resource_guard_failed');return
            except Exception:self._abort('resource_monitor_unavailable');return

    def start(self):
        require(self.proc is None,'supervisor_already_started')
        if self.options.get('mode')!='mock':
            if self.options.get('execution_authorized') is not True:raise ExecutionDisabled('explicit_execution_required')
            grant=load_grant(self.options.get('approval'),self.options.get('approval_sha'),self.options.get('manifest'),
                             self.options.get('plan'),self.options.get('evidence_root'))
            require(grant.record['traffic_kind']=='real','real_grant_required')
            require(os.name=='nt','windows_runtime_required')
            claim_grant(grant,self.options['storage_root'],worker_start=True)
            require(self.timeout==limits()['max_run_seconds'],'real_deadline_override_forbidden')
            # Real mode always uses the frozen monitor; test callbacks cannot replace it.
            def real_resources():
                from .readiness import resource_codes,resource_snapshot
                from .storage import physical_bytes
                codes=resource_codes(resource_snapshot(self.options['storage_root']),running=True)
                if physical_bytes(self.options['storage_root'])>limits()['max_physical_storage_bytes']:
                    codes.append('private_storage_guard_failed')
                return codes
            self.resource_check=real_resources
        self.deadline=time.monotonic()+self.timeout
        ctx=multiprocessing.get_context('spawn');self.conn,child=ctx.Pipe(duplex=True)
        self.proc=ctx.Process(target=run_worker,args=(child,self.options),daemon=True)
        # Child waits for boot before imports/model activity. Assignment failure stops it.
        try:
            if os.name=='nt':self.job=WindowsJob(limits()['max_worker_tree_bytes'])
            self.proc.start();child.close()
            if self.job:self.job.assign(self.proc.pid)
            self.watchdog=threading.Thread(target=self._watch,daemon=True);self.watchdog.start()
            self.monitor=threading.Thread(target=self._monitor,daemon=True);self.monitor.start()
            send(self.conn,{'kind':'boot'})
            result=self._next()
            if result.get('kind')!='ready':
                code=result.get('code') if result.get('code') in SAFE_ERROR_CODES else 'worker_boot_failed'
                raise RuntimeFailure(code,'not_sent')
        except BaseException:
            self._abort('worker_boot_failed');self.close();raise

    def _next(self):
        while True:
            if self.failure:raise RuntimeFailure(self.failure,'unknown' if self.generation_dispatched else 'not_sent')
            if self.conn.poll(0.02):
                try:return receive(self.conn)
                except (EOFError,OSError,IntegrityError):raise RuntimeFailure(self.failure or 'worker_transport_lost','unknown' if self.generation_dispatched else 'not_sent') from None
            if not self.proc.is_alive():raise RuntimeFailure(self.failure or 'worker_crashed','unknown' if self.generation_dispatched else 'not_sent')

    def infer(self,query,on_prepared):
        require(self.proc is not None and self.deadline is not None,'supervisor_not_started')
        require(self.requests<4 and self.failure is None and time.monotonic()<self.deadline,'runtime_budget_exhausted')
        self.requests+=1;self.generation_dispatched=False
        try:
            send(self.conn,{'kind':'prepare','query':query});prepared=self._next()
            if prepared.get('kind')!='prepared':
                code=prepared.get('code') if prepared.get('code') in SAFE_ERROR_CODES else 'prepare_failed'
                raise RuntimeFailure(code,'not_sent')
            ids=prepared.get('input_ids')
            require(type(ids) is list and ids and all(type(i) is int and i>=0 for i in ids)
                    and type(prepared.get('input_tokens')) is int
                    and prepared.get('input_tokens')==len(ids)<=limits()['max_input_tokens'],'worker_input_usage_invalid')
            require(self.input_total+len(ids)<=limits()['max_total_input_tokens'],'total_input_token_cap_exceeded')
            require(self.output_total+limits()['max_output_tokens']<=limits()['max_total_output_tokens'],'total_output_token_reserve_exceeded')
            # Durable prepared token/rendering provenance BEFORE permitting generate.
            on_prepared(prepared)
            self.input_total+=len(ids);self.generation_dispatched=True
            send(self.conn,{'kind':'generate'})
            acknowledgement=self._next()
            if acknowledgement.get('kind')!='accepted':raise RuntimeFailure('dispatch_ack_missing','unknown')
            result=self._next()
            if result.get('kind')=='error':
                code=result.get('code') if result.get('code') in SAFE_ERROR_CODES else 'generation_failed'
                raise RuntimeFailure(code,'accepted' if result.get('delivery')=='accepted' else 'unknown')
            require(result.get('kind')=='result' and type(result.get('text')) is str,'worker_output_invalid')
            ids=result.get('output_ids')
            require(type(ids) is list and 1<=len(ids)<=limits()['max_output_tokens']
                    and all(type(i) is int and i>=0 for i in ids)
                    and type(result.get('output_tokens')) is int and type(result.get('input_tokens')) is int
                    and result.get('output_tokens')==len(ids) and result.get('input_tokens')==prepared['input_tokens'],'worker_output_usage_invalid')
            require(len(result['text'].encode())<=limits()['max_response_bytes'],'output_byte_cap_exceeded')
            require(type(result.get('gpu_peak_reserved_bytes')) is int and 0<=result['gpu_peak_reserved_bytes']<=limits()['max_gpu_reserved_bytes'],'gpu_reserved_cap_exceeded')
            self.output_total+=len(ids)
            return result
        except BaseException as exc:
            prior=self.failure
            self._abort('run_stopped_after_failure')
            if isinstance(exc,RuntimeFailure):raise
            if isinstance(exc,(KeyboardInterrupt,SystemExit)):raise
            raise RuntimeFailure(prior or 'runtime_validation_failed','unknown' if self.generation_dispatched else 'not_sent') from None

    def close(self):
        self.done.set()
        if self.conn:
            try:
                if self.proc and self.proc.is_alive():send(self.conn,{'kind':'close'})
            except (OSError,EOFError):pass
        if self.proc and self.proc.pid:
            self.proc.join(0.3)
            if self.proc.is_alive():
                if self.job:self.job.terminate()
                try:self.proc.kill()
                except OSError:pass
                self.proc.join(2)
        with self.lock:
            if self.job:self.job.close();self.job=None
        if self.conn:self.conn.close();self.conn=None
        for thread in [self.watchdog,self.monitor]:
            if thread and thread is not threading.current_thread():thread.join(0.3)
        require(self.proc is None or self.proc.pid is None or not self.proc.is_alive(),'worker_cleanup_failed')

    def __enter__(self):self.start();return self
    def __exit__(self,*_):self.close()
