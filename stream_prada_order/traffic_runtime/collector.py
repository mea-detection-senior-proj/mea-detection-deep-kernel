"""Bounded H collector on G's unmodified event schema/store/recovery contract."""
import copy
import time
import unicodedata
import uuid

from ..traffic_collection.collector import Collector as GCollector, recover
from ..traffic_collection.schema import require, digest, canonical, IntegrityError
from ..traffic_collection.adapters import AdapterResponse, AdapterFailure
from .policy import profile, limits, validate_manifest_plan


class RuntimeCollector(GCollector):
    """G remains mock-only; this explicit sibling supplies authorized real admission.

    No monkeypatching, identity spoofing, schema migration, or old evidence writes.
    The first pilot is homogeneous benign, one native session, one attempt/request.
    """
    def __init__(self,store,manifest,plan,adapter):
        validate_manifest_plan(manifest,plan)
        require(adapter.manifest==manifest and adapter.plan==plan and adapter.identity==manifest['victim'],'adapter_manifest_mismatch')
        require(adapter.store is store and not store.state.runs,'fresh_pilot_store_required')
        self.store,self.adapter=store,adapter;self.manifest=copy.deepcopy(manifest);self.plan=copy.deepcopy(plan)
        self.run_id=manifest['run_id'];self.failed=False;self.session_opened=False
        self.store.max_logical_bytes=min(store.max_logical_bytes,manifest['budget']['max_logical_storage_bytes'])
        self.store.append('run_opened',self.run_id,data={'manifest':self.manifest})

    def start(self):
        try:self.adapter.start()
        except BaseException:
            self.failed=True;recover(self.store);raise

    def open_session(self,session_id,native_session_sha256):
        require(not self.session_opened and session_id==self.plan['session_id'] and
                native_session_sha256==self.plan['native_session_sha256'],'native_session_plan_mismatch')
        result=super().open_session(session_id,native_session_sha256);self.session_opened=True;return result

    def collect(self,session_id,request_id,query,document_ids,task_id,format_class,decision=None):
        try:return self._collect(session_id,request_id,query,document_ids,task_id,format_class,decision)
        except BaseException:
            self.failed=True;self.adapter.close();raise

    def _collect(self,session_id,request_id,query,document_ids,task_id,format_class,decision=None):
        with self.store.mutex:
            require(self.adapter.started and not self.adapter.closed and not self.failed,'runtime_not_available')
            require(self.adapter.identity==self.manifest['victim'] and self.adapter.manifest==self.manifest
                    and self.adapter.plan==self.plan,'runtime_identity_or_plan_changed')
            require(self.adapter.is_mock is (self.manifest['traffic_kind']=='mock'),'runtime_kind_changed')
            self.adapter._authorize()
            require(session_id==self.plan['session_id'] and session_id in self.store.state.sessions and
                    not self.store.state.sessions[session_id]['closed'],'session_not_open')
            run=self.store.state.runs[self.run_id];session=self.store.state.sessions[session_id]
            b=self.manifest['budget'];index=run['requests']
            require(index<len(self.plan['queries']) and run['attempts']<b['max_attempts']
                    and session['attempts']<b['max_session_attempts'],'request_budget_exhausted')
            require(type(query) is str and query.strip() and len(query.encode())<=b['max_query_bytes'],'input_byte_cap_exceeded')
            expected={'request_id':request_id,'query_sha256':digest(query),'document_ids':list(document_ids),
                      'task_id':task_id,'format_class':format_class}
            require(expected==self.plan['queries'][index],'query_does_not_match_frozen_plan')
            require(decision is None,'benign_pilot_has_no_response_dependent_selection')
            require(request_id not in self.store.state.requests,'duplicate_request_id')
            self.store.guard(262144)
            require(self.store.logical_bytes()+len(query.encode())+262144<=self.store.max_logical_bytes,'storage_reserve_insufficient')
            normalized=' '.join(unicodedata.normalize('NFKC',query).casefold().split())
            qsha=self.store.write_blob(query.encode())
            self.store.append('request_started',self.run_id,session_id,request_id,{
                'request_sequence':index+1,'session_request_sequence':session['requests']+1,
                'query_sha256':qsha,'normalized_query_sha256':digest(normalized),'query_bytes':len(query.encode()),
                'words':len(query.split()),'characters':len(query),'document_ids':list(document_ids),'task_id':task_id,
                'format_class':format_class,'decision':{'sha256':None,'based_on_attempt_ids':[]}})
            aid=uuid.uuid4().hex
            self.store.append('attempt_started',self.run_id,session_id,request_id,{'attempt_id':aid,'attempt_number':1,
                              'dispatch_sequence':run['attempts']+1,'retry_of':None})
            context={'run_id':self.run_id,'session_id':session_id,'request_id':request_id,'attempt_id':aid}
            try:
                result=self.adapter.respond(query,context)
                require(isinstance(result,AdapterResponse) and type(result.text) is str,'invalid_runtime_response')
                require(type(result.input_tokens) is int and 1<=result.input_tokens<=limits()['max_input_tokens']
                        and type(result.output_tokens) is int and 1<=result.output_tokens<=limits()['max_output_tokens'],'invalid_runtime_usage')
                require(result.token_origin==('mock_reported' if self.adapter.is_mock else 'adapter_reported'),'token_origin_mismatch')
                require(len(result.text.encode())<=b['max_response_bytes'],'output_byte_cap_exceeded')
            except Exception as exc:
                delivery=exc.delivery if isinstance(exc,AdapterFailure) and exc.delivery in {'accepted','not_sent','unknown'} else 'unknown'
                code='timeout' if isinstance(exc,AdapterFailure) and exc.code=='timeout' else 'adapter_failure'
                self.store.append('attempt_failed',self.run_id,session_id,request_id,{'attempt_id':aid,'code':code,
                                  'delivery':delivery,'retryable':False})
                status='unknown' if delivery=='unknown' else 'failed';self.failed=True
                self.store.append('request_finished',self.run_id,session_id,request_id,
                                  {'status':status,'recovered':False,'reason':'adapter_failure'})
                self.adapter.close();recover(self.store)
                return {'request_id':request_id,'status':status,'response_sha256':None}
            response=self.store.write_blob(result.text.encode())
            self.store.append('attempt_succeeded',self.run_id,session_id,request_id,{'attempt_id':aid,
                    'response_sha256':response,'response_bytes':len(result.text.encode()),'input_tokens':result.input_tokens,
                    'output_tokens':result.output_tokens,'token_origin':result.token_origin,'delivery':'accepted'})
            self.store.append('request_finished',self.run_id,session_id,request_id,
                              {'status':'succeeded','recovered':False,'reason':'completed'})
            return {'request_id':request_id,'status':'succeeded','response_sha256':response}

    def close_run(self):
        require(not self.failed and self.store.state.runs[self.run_id]['requests']==len(self.plan['queries']),'pilot_incomplete')
        deadline=self.adapter.supervisor.deadline
        self.adapter.close()
        if deadline is None or time.monotonic()>=deadline or self.adapter.supervisor.failure:
            self.failed=True;recover(self.store);require(False,'pilot_deadline_or_guard_failed')
        return super().close_run()
