"""Numeric-only mock plans and fake tokenization/tensors; never real model data."""
from contextlib import nullcontext
import json
from pathlib import Path

from phase_g_helpers import manifest
from stream_prada_order.traffic_collection.schema import canonical,digest
from stream_prada_order.traffic_runtime.policy import profile,limits,bindings


def plan(count=1,kind='mock'):
    cfg=manifest();cfg['traffic_kind']=kind;cfg['victim']=profile()['identity']
    cfg['budget'].update(max_requests=4,max_attempts=4,max_attempts_per_request=1,max_session_attempts=4,
                         max_query_bytes=65536,max_response_bytes=16384,max_logical_storage_bytes=4194304)
    queries=[str(n+1)+' 2' for n in range(count)]
    p={'schema_version':'qwen-query-plan-v1','run_id':cfg['run_id'],'session_id':'s1',
       'native_session_sha256':digest('7'),'queries':[{'request_id':'q'+str(n+1),'query_sha256':digest(q),
        'document_ids':['doc1'],'task_id':'task1','format_class':'other'} for n,q in enumerate(queries)]}
    return cfg,p,queries


def grant_files(folder,cfg,p):
    folder=Path(folder);evidence=folder/'evidence';evidence.mkdir()
    refs={}
    for name,raw in [('operator_authorization',b'4'),('model_license',b'5'),('source_authorization',b'6'),('privacy_review',b'7')]:
        sha=digest(raw);(evidence/(sha+'.private')).write_bytes(raw);refs[name]=sha
    record={'schema_version':'qwen-execution-grant-v1','grant_id':'numeric-mock-only',
            'purpose':'four_request_benign_readiness','traffic_kind':cfg['traffic_kind'],'execution_authorized':True,
            'issued_utc':'2026-01-01T00:00:00Z','expires_utc':'2026-01-01T01:00:00Z',
            'bindings':bindings(cfg,p),'limits':limits(),'evidence':refs}
    path=folder/'grant.private';raw=canonical(record).encode();path.write_bytes(raw)
    return path,digest(raw),evidence,record


class FakeTensor:
    def __init__(self,value):self.value=value
    def __getitem__(self,index):return FakeTensor(self.value[index])
    def tolist(self):return self.value
    def to(self,device):return self


class FakeTokenizer:
    def __init__(self):self.calls=[]
    def apply_chat_template(self,messages,**kwargs):
        self.calls.append(('render',messages,kwargs));return '1 2 3'
    def __call__(self,text,**kwargs):
        self.calls.append(('tokenize',text,kwargs));return {'input_ids':FakeTensor([[1,2,3]]),'attention_mask':FakeTensor([[1,1,1]])}
    def decode(self,ids,**kwargs):self.calls.append(('decode',ids,kwargs));return '4'


class FakeModel:
    def __init__(self):self.kwargs=None
    def generate(self,**kwargs):
        self.kwargs=kwargs
        return type('Output',(),{'sequences':FakeTensor([[1,2,3,4,151645]])})()


class FakeCuda:
    def max_memory_reserved(self,*_):return 0
    def synchronize(self,*_):pass


class FakeTorch:
    cuda=FakeCuda()
    def inference_mode(self):return nullcontext()


def fake_backend():
    from stream_prada_order.traffic_runtime.backend import QwenBackend
    b=QwenBackend();b.tokenizer=FakeTokenizer();b.model=FakeModel();b.torch=FakeTorch()
    b.GenerationConfig=lambda **kwargs:kwargs
    return b
