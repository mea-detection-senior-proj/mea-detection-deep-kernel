"""Read-only join of G journal with H private receipts; no model/tokenizer loads."""
from pathlib import Path

from ..traffic_collection.audit import audit
from ..traffic_collection.store import read_events
from ..traffic_collection.state import replay
from ..traffic_collection.schema import require,digest,canonical
from .policy import profile,limits,file_digest,HERE
from .storage import read_receipt,physical_bytes


def runtime_audit(root):
    root=Path(root);events=read_events(root);base=audit(root)
    require(read_events(root)==events,'concurrent_write_retry_audit')
    state=replay(events);verified=missing=0;known_inputs=known_outputs=0;codes=[]
    for aid,attempt in state.attempts.items():
        success=attempt['outcome']=='attempt_succeeded';request=state.requests[attempt['request_id']]
        manifest=state.runs[attempt['run_id']]['manifest']
        if not (root/'runtime_receipts'/(aid+'.binding.private')).exists():
            require(not success,'successful_runtime_binding_missing');missing+=1;continue
        binding=read_receipt(root,aid,'binding')
        require(binding['run_id']==attempt['run_id'] and binding['session_id']==attempt['session_id']
                and binding['request_id']==attempt['request_id'] and binding['query_sha256']==request['data']['query_sha256'],
                'runtime_binding_mismatch')
        require(binding['bindings']['manifest_sha256']==digest(canonical(manifest)),'runtime_manifest_hash_mismatch')
        require(binding['bindings']['profile_sha256']==file_digest(HERE/'profile_v1.json'),'runtime_profile_hash_mismatch')
        if not success:continue
        prepared=read_receipt(root,aid,'prepared');outcome=read_receipt(root,aid,'outcome')
        require(prepared['chat_template_sha256']==profile()['chat_template_sha256']
                and digest(prepared['rendered_prompt'])==prepared['rendered_prompt_sha256'],'runtime_rendering_corrupt')
        require(type(prepared['input_ids']) is list and len(prepared['input_ids'])==prepared['input_tokens']
                ==attempt['result']['input_tokens'] and 1<=prepared['input_tokens']<=limits()['max_input_tokens'],'runtime_input_usage_mismatch')
        require(type(outcome['output_ids']) is list and len(outcome['output_ids'])==outcome['output_tokens']
                ==attempt['result']['output_tokens'] and 1<=outcome['output_tokens']<=limits()['max_output_tokens'],'runtime_output_usage_mismatch')
        require(outcome['input_tokens']==prepared['input_tokens'] and outcome['status']=='succeeded'
                and outcome['response_sha256']==attempt['result']['response_sha256'],'runtime_outcome_mismatch')
        require(attempt['finished']['clock_epoch']==binding['clock_epoch'] and
                attempt['finished']['monotonic_ns']<=binding['deadline_monotonic_ns'],'runtime_deadline_exceeded')
        known_inputs+=prepared['input_tokens'];known_outputs+=outcome['output_tokens'];verified+=1
    require(len(state.runs)<=1 and len(state.sessions)<=1 and len(state.attempts)<=4,'pilot_structure_exceeded')
    require(known_inputs<=limits()['max_total_input_tokens'] and known_outputs<=limits()['max_total_output_tokens'],'pilot_total_usage_exceeded')
    return {'schema_version':'qwen-runtime-audit-v1','status':'valid','evidence_kind':base['evidence_kind'],
            'verified_successful_runtime_attempts':verified,'attempts_without_binding_receipt':missing,
            'successful_input_tokens':known_inputs,'successful_output_tokens':known_outputs,
            'failed_or_unknown_output_usage':'unavailable_not_imputed',
            'physical_bytes':physical_bytes(root),'original_collector_audit':base,
            'real_runtime_generalization_verified':False,'detector_metrics_computed':False}
