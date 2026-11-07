"""Offline checks inspect numeric temporary files, never real weights."""
from pathlib import Path
import hashlib
import sys
import tempfile
import unittest
import contextlib
import io
import json
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from stream_prada_order.traffic_runtime.readiness import inspect_snapshot,readiness,resource_codes
from stream_prada_order.traffic_runtime.policy import limits,environment_lock
from stream_prada_order.traffic_collection.schema import digest
from stream_prada_order.traffic_runtime.__main__ import main


class ReadinessTests(unittest.TestCase):
    def setUp(self):self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
    def tearDown(self):self.temp.cleanup()

    def test_missing_snapshot_blocks_without_loading_anything(self):
        result=inspect_snapshot(self.root/'missing')
        self.assertEqual(result['codes'],['snapshot_missing']);self.assertEqual(result['bytes_read'],0)

    def test_hash_verification_uses_expected_digest_not_self_certification(self):
        raw=b'123';(self.root/'model.safetensors').write_bytes(raw)
        lock={'files':{'model.safetensors':{'bytes':3,'sha256':digest(raw),'git_blob_sha1':'0'*40}}}
        self.assertEqual(inspect_snapshot(self.root,lock)['status'],'passed')
        (self.root/'model.safetensors').write_bytes(b'456')
        self.assertIn('snapshot_hash_mismatch',inspect_snapshot(self.root,lock)['codes'])

    def test_git_blob_identity_size_and_read_budget(self):
        raw=b'123';(self.root/'config.json').write_bytes(raw)
        lock={'files':{'config.json':{'bytes':3,'sha256':None,'git_blob_sha1':hashlib.sha1(b'blob 3\0'+raw).hexdigest()}}}
        self.assertEqual(inspect_snapshot(self.root,lock)['status'],'passed')
        self.assertIn('snapshot_read_budget_exceeded',inspect_snapshot(self.root,lock,read_cap=2)['codes'])
        (self.root/'config.json').write_bytes(b'1234')
        self.assertIn('snapshot_size_mismatch',inspect_snapshot(self.root,lock)['codes'])

    def test_unreviewed_snapshot_code_is_not_accepted(self):
        (self.root/'custom.py').write_bytes(b'123')
        result=inspect_snapshot(self.root,{'files':{}})
        self.assertIn('snapshot_unreviewed_extra_files',result['codes'])

    def test_resources_fail_closed_for_unknown_or_below_gates(self):
        self.assertTrue(resource_codes({}))
        e=environment_lock();l=limits()
        r={'available_ram_bytes':l['min_available_ram_bytes'],'disk_free_bytes':l['min_disk_free_bytes'],
           'gpu_free_bytes':l['min_gpu_free_bytes'],'gpu_name':e['reviewed_gpu'],'driver':e['reviewed_driver']}
        self.assertFalse(resource_codes(r));r['gpu_free_bytes']-=1
        self.assertIn('gpu_free_bytes_gate_failed',resource_codes(r))

    def test_readiness_never_enables_execution_even_when_static_checks_pass(self):
        with patch('stream_prada_order.traffic_runtime.readiness.inspect_snapshot',return_value={'status':'passed','codes':[]}), \
             patch('stream_prada_order.traffic_runtime.readiness.environment',return_value={'status':'passed_static_only','codes':[]}), \
             patch('stream_prada_order.traffic_runtime.readiness.resource_snapshot',return_value={}), \
             patch('stream_prada_order.traffic_runtime.readiness.resource_codes',return_value=[]):
            result=readiness()
        self.assertEqual(result['status'],'BLOCKED');self.assertFalse(result['real_execution_enabled'])
        self.assertFalse(result['native_inference_verified'])

    def test_describe_cli_does_not_enable_execution(self):
        output=io.StringIO()
        with contextlib.redirect_stdout(output):self.assertEqual(main(['describe']),0)
        self.assertFalse(json.loads(output.getvalue())['real_execution_enabled'])

    def test_cli_errors_do_not_expose_private_paths_or_create_missing_stores(self):
        path=self.root/'11223344-secret';output=io.StringIO()
        with contextlib.redirect_stdout(output):self.assertEqual(main(['audit','--root',str(path)]),2)
        self.assertNotIn('11223344',output.getvalue());self.assertFalse(path.exists())


if __name__=='__main__':unittest.main()
