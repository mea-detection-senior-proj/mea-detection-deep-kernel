"""Physical storage headroom guard and immutable, per-attempt private receipts."""
import json
import os
from pathlib import Path
import shutil
import uuid

from ..traffic_collection.store import EventStore, _check_ignored_paths
from ..traffic_collection.schema import require, canonical, digest, strict_json
from .policy import limits


def physical_bytes(root):
    total=0
    for path in Path(root).rglob('*'):
        require(not path.is_symlink(),'private_storage_symlink_rejected')
        try:
            if path.is_file():total+=path.stat().st_size
        except FileNotFoundError:pass  # A committed journal/part file may disappear during sampling.
    return total


class RuntimeStore(EventStore):
    def __init__(self,root,**kwargs):
        super().__init__(root,max_logical_bytes=limits()['max_logical_storage_bytes'],**kwargs)

    def guard(self,reserve=65536):
        require(physical_bytes(self.root)+reserve<=limits()['max_physical_storage_bytes'],'physical_storage_cap_exceeded')
        require(shutil.disk_usage(self.root).free>=limits()['min_disk_free_bytes']+reserve,'disk_free_gate_failed')

    def logical_bytes(self):
        return super().logical_bytes()+sum(p.stat().st_size for p in (self.root/'runtime_receipts').glob('*') if p.is_file())

    def append(self,*args,**kwargs):
        self.guard();return super().append(*args,**kwargs)

    def write_blob(self,raw):
        self.guard(65536+len(raw)*2);return super().write_blob(raw)

    def receipt(self,attempt_id,stage,value):
        require(len(attempt_id)==32 and all(c in '0123456789abcdef' for c in attempt_id),'receipt_attempt_invalid')
        require(stage in {'prepared','outcome','binding'},'receipt_stage_invalid')
        body=canonical({'schema_version':'qwen-private-receipt-v1','attempt_id':attempt_id,'stage':stage,'data':value})
        raw=canonical({'body':body,'sha256':digest(body)}).encode()
        self.guard(65536+2*len(raw))
        # Sidecars count toward the same logical cap, not only the physical cap.
        require(self.logical_bytes()+len(raw)<=self.max_logical_bytes,'storage_budget_exhausted')
        folder=self.root/'runtime_receipts';folder.mkdir(exist_ok=True)
        target=folder/(attempt_id+'.'+stage+'.private');temporary=folder/('part-'+uuid.uuid4().hex)
        _check_ignored_paths(self.root,[target.relative_to(self.root).as_posix(),temporary.relative_to(self.root).as_posix()])
        require(not target.exists(),'immutable_receipt_exists')
        with temporary.open('xb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
        os.link(temporary,target);temporary.unlink()
        return digest(raw)


def read_receipt(root,attempt_id,stage):
    path=Path(root)/'runtime_receipts'/(attempt_id+'.'+stage+'.private')
    require(path.is_file() and not path.is_symlink(),'receipt_missing')
    with path.open('rb') as f:raw=f.read(262145)
    require(len(raw)<=262144,'receipt_size_exceeded')
    envelope=strict_json(raw)
    require(type(envelope) is dict and set(envelope)=={'body','sha256'} and type(envelope['body']) is str,'receipt_corrupt')
    require(digest(envelope['body'])==envelope['sha256'],'receipt_corrupt')
    body=strict_json(envelope['body'])
    require(type(body) is dict and set(body)=={'schema_version','attempt_id','stage','data'},'receipt_corrupt')
    require(body['schema_version']=='qwen-private-receipt-v1' and body['attempt_id']==attempt_id and body['stage']==stage,'receipt_binding_mismatch')
    return body['data']
