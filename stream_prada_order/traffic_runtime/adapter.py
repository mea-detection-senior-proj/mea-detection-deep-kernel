"""Local runtime adapter. Disabled by default; explicit benign grant for real mode."""
import copy
import time

from ..traffic_collection.adapters import AdapterResponse
from ..traffic_collection.schema import require, ExecutionDisabled, digest, canonical
from .policy import profile, limits, bindings, validate_manifest_plan, load_grant, claim_grant
from .readiness import inspect_snapshot, environment, resource_snapshot, resource_codes
from .supervisor import Supervisor, RuntimeFailure


class LocalQwenAdapter:
    def __init__(self,store,manifest,plan,*,execution_authorized=False,snapshot=None,
                 approval=None,approval_sha=None,evidence_root=None,mock=False,mock_options=None,
                 timeout=None,resource_check=None):
        validate_manifest_plan(manifest,plan)
        require(not store.state.runs,'fresh_pilot_store_required')
        require(mock is (manifest['traffic_kind']=='mock'),'adapter_traffic_kind_mismatch')
        self.store=store;self.manifest=copy.deepcopy(manifest);self.plan=copy.deepcopy(plan)
        self.is_mock=mock;self.execution_authorized=execution_authorized
        self.identity=copy.deepcopy(profile()['identity']);self.grant=None
        self.approval,self.approval_sha,self.evidence_root=approval,approval_sha,evidence_root
        self.snapshot=snapshot;self.started=False;self.closed=False
        self.options={'mode':'mock' if mock else 'real','mock_marker':'numeric-tests-only',
                      'template_sha256':profile()['chat_template_sha256']}
        if mock:
            allowed={'boot_hang','boot_failure','prepare_crash','generate_crash','generate_hang','generate_failure','input_ids'}
            require(set(mock_options or {})<=allowed,'mock_option_invalid')
            self.options.update(copy.deepcopy(mock_options or {}))
        else:
            require(mock_options is None and timeout is None and resource_check is None,'real_override_forbidden')
        def guards():
            store.guard()
            return resource_codes(resource_snapshot(store.root),running=True) if not mock else []
        self.supervisor=Supervisor(self.options,timeout=timeout,resource_check=resource_check or guards)

    def _authorize(self):
        if self.is_mock:return
        if self.execution_authorized is not True:raise ExecutionDisabled('real_execution_disabled_by_default')
        self.grant=load_grant(self.approval,self.approval_sha,self.manifest,self.plan,self.evidence_root)
        require(self.grant.record['traffic_kind']=='real','real_grant_required')

    def start(self):
        require(not self.closed and not self.started,'adapter_already_started_or_closed')
        self._authorize()
        if not self.is_mock:
            require(self.snapshot is not None and inspect_snapshot(self.snapshot)['status']=='passed','pinned_snapshot_unavailable')
            require(environment()['status']=='passed_static_only','environment_static_checks_failed')
            require(not resource_codes(resource_snapshot(self.store.root)),'resource_preflight_failed')
            claim_grant(self.grant,self.store.root)
            self.options.update(execution_authorized=True,snapshot=str(self.snapshot),approval=str(self.approval),
                                approval_sha=self.approval_sha,evidence_root=str(self.evidence_root),
                                manifest=self.manifest,plan=self.plan,storage_root=str(self.store.root))
            self.supervisor.options=dict(self.options)
        self.supervisor.start();self.started=True

    def respond(self,query,context):
        require(self.started and not self.closed,'runtime_not_started')
        self._authorize();aid=context['attempt_id'];prepared={}
        self.store.receipt(aid,'binding',{'bindings':bindings(self.manifest,self.plan),
                'grant_sha256':None if self.is_mock else self.grant.sha,'query_sha256':digest(query),
                'run_id':context['run_id'],'session_id':context['session_id'],'request_id':context['request_id'],
                'traffic_kind':'mock' if self.is_mock else 'real','clock_epoch':self.store.clock_epoch,
                'supervisor_start_monotonic_ns':int((self.supervisor.deadline-self.supervisor.timeout)*10**9),
                'deadline_monotonic_ns':int(self.supervisor.deadline*10**9)})
        def before_generate(value):
            require(value['chat_template_sha256']==profile()['chat_template_sha256'],'worker_template_mismatch')
            require(digest(value['rendered_prompt'])==value['rendered_prompt_sha256'],'worker_prompt_hash_mismatch')
            prepared.update(value);self.store.receipt(aid,'prepared',value)
        try:
            result=self.supervisor.infer(query,before_generate)
        except RuntimeFailure as exc:
            self.store.receipt(aid,'outcome',{'status':'failed','code':exc.runtime_code,'delivery':exc.delivery,
                    'guard_codes':list(self.supervisor.guard_codes),
                    'input_tokens':prepared.get('input_tokens'),'output_tokens':None,'output_ids':None})
            raise
        self.store.receipt(aid,'outcome',{'status':'succeeded','delivery':'accepted','response_sha256':digest(result['text']),
                            'input_tokens':result['input_tokens'],'output_tokens':result['output_tokens'],
                            'output_ids':result['output_ids'],'gpu_peak_reserved_bytes':result['gpu_peak_reserved_bytes']})
        return AdapterResponse(result['text'],result['input_tokens'],result['output_tokens'],
                               'mock_reported' if self.is_mock else 'adapter_reported')

    def close(self):
        self.supervisor.close();self.closed=True
