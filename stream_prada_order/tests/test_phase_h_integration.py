"""Real collector/SQLite/process supervision with fake inference only."""
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from phase_h_helpers import plan
from stream_prada_order.traffic_runtime.adapter import LocalQwenAdapter
from stream_prada_order.traffic_runtime.collector import RuntimeCollector
from stream_prada_order.traffic_runtime.storage import RuntimeStore,read_receipt
from stream_prada_order.traffic_runtime.audit import runtime_audit
from stream_prada_order.traffic_collection.collector import recover
from stream_prada_order.traffic_collection.schema import IntegrityError,ExecutionDisabled
from stream_prada_order.traffic_collection.views import attempt_records


class IntegrationTests(unittest.TestCase):
    def setUp(self):self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)/'private';self.store=RuntimeStore(self.root);self.adapter=None
    def tearDown(self):
        if self.adapter:self.adapter.close()
        self.store.close();self.temp.cleanup()

    def start(self,count=1,**options):
        cfg,p,queries=plan(count);self.adapter=LocalQwenAdapter(self.store,cfg,p,mock=True,timeout=10,mock_options=options)
        c=RuntimeCollector(self.store,cfg,p,self.adapter);c.start();c.open_session('s1',p['native_session_sha256'])
        return c,p,queries

    def test_four_requests_preserve_native_chronology_exact_usage_and_receipts(self):
        c,p,queries=self.start(4)
        for spec,q in zip(p['queries'],queries):
            result=c.collect('s1',spec['request_id'],q,['doc1'],'task1','other')
            self.assertEqual(result['status'],'succeeded')
        c.close_session('s1');c.close_run()
        rows=list(attempt_records(self.root))
        self.assertEqual([r['dispatch_sequence'] for r in rows],[1,2,3,4])
        self.assertEqual([r['input_tokens'] for r in rows],[3]*4)
        self.assertEqual([r['output_tokens'] for r in rows],[2]*4)
        self.assertEqual(runtime_audit(self.root)['verified_successful_runtime_attempts'],4)
        prepared=read_receipt(self.root,rows[0]['attempt_id'],'prepared')
        self.assertEqual(prepared['input_ids'],[1,2,3])
        self.assertNotIn('rendered_prompt',str(self.store.events()))
        self.assertEqual(recover(self.store)['unknown_attempts'],0)

    def test_frozen_query_order_and_second_session_are_enforced(self):
        c,p,q=self.start(2)
        with self.assertRaisesRegex(IntegrityError,'frozen_plan'):c.collect('s1','q2',q[1],['doc1'],'task1','other')
        self.assertEqual(self.adapter.supervisor.requests,0)
        c.close_session('s1')
        with self.assertRaisesRegex(IntegrityError,'session_plan'):c.open_session('s2',p['native_session_sha256'])

    def test_unknown_delivery_stops_run_without_retry(self):
        c,p,q=self.start(generate_crash=True)
        result=c.collect('s1','q1',q[0],['doc1'],'task1','other')
        self.assertEqual(result['status'],'unknown');self.assertEqual(self.adapter.supervisor.requests,1)
        rows=list(attempt_records(self.root));self.assertEqual(len(rows),1)
        self.assertIsNone(rows[0]['response_utc']);self.assertFalse(rows[0]['outcome']=='attempt_succeeded')
        self.assertTrue(self.store.state.runs[c.run_id]['closed'])
        self.assertEqual(recover(self.store)['unknown_attempts'],0)

    def test_input_token_cap_fails_before_generate_and_has_no_retry(self):
        c,p,q=self.start(input_ids=[1]*2049)
        result=c.collect('s1','q1',q[0],['doc1'],'task1','other')
        self.assertEqual(result['status'],'failed')
        self.assertEqual(list(attempt_records(self.root))[0]['delivery'],'not_sent')
        self.assertEqual(self.adapter.supervisor.requests,1)
        aid=next(iter(self.store.state.attempts))
        self.assertEqual(read_receipt(self.root,aid,'outcome')['code'],'input_token_cap_exceeded')

    def test_previously_used_store_is_not_reused_for_a_new_budget(self):
        c,p,q=self.start();c.collect('s1','q1',q[0],['doc1'],'task1','other');c.close_session('s1');c.close_run()
        cfg,p,q=plan()
        with self.assertRaisesRegex(IntegrityError,'fresh_pilot'):LocalQwenAdapter(self.store,cfg,p,mock=True)

    def test_real_execution_default_rejected_before_worker_spawn(self):
        cfg,p,q=plan(kind='real');self.adapter=LocalQwenAdapter(self.store,cfg,p)
        c=RuntimeCollector(self.store,cfg,p,self.adapter)
        with self.assertRaises(ExecutionDisabled):c.start()
        self.assertIsNone(self.adapter.supervisor.proc)
        self.assertEqual(len(self.store.state.attempts),0)

    def test_receipt_is_immutable_and_corruption_is_rejected(self):
        c,p,q=self.start();c.collect('s1','q1',q[0],['doc1'],'task1','other');c.close_session('s1');c.close_run()
        aid=next(iter(self.store.state.attempts))
        with self.assertRaisesRegex(IntegrityError,'immutable_receipt'):self.store.receipt(aid,'prepared',{})
        path=self.root/'runtime_receipts'/(aid+'.prepared.private');path.write_bytes(b'123')
        with self.assertRaises(IntegrityError):runtime_audit(self.root)

    def test_physical_storage_limit_stops_before_model_request(self):
        c,p,q=self.start()
        with (self.root/'numeric-fixture.private').open('wb') as f:f.truncate(20*1024**2)
        with self.assertRaisesRegex(IntegrityError,'physical_storage'):c.collect('s1','q1',q[0],['doc1'],'task1','other')
        self.assertEqual(self.adapter.supervisor.requests,0)

    def test_durable_runtime_result_before_collector_commit_recovers_as_unknown_without_resend(self):
        c,p,q=self.start();original=self.store.append
        def interrupted(kind,*args,**kwargs):
            if kind=='attempt_succeeded':raise SystemExit(73)
            return original(kind,*args,**kwargs)
        with patch.object(self.store,'append',side_effect=interrupted):
            with self.assertRaises(SystemExit):c.collect('s1','q1',q[0],['doc1'],'task1','other')
        self.assertFalse(self.adapter.supervisor.proc.is_alive())
        aid=next(iter(self.store.state.attempts))
        self.assertEqual(read_receipt(self.root,aid,'outcome')['status'],'succeeded')
        self.store.close();self.store=RuntimeStore(self.root)
        self.assertEqual(recover(self.store)['unknown_attempts'],1)
        rows=list(attempt_records(self.root));self.assertEqual(rows[0]['delivery'],'unknown')
        self.assertIsNone(rows[0]['response_utc'])
        self.assertEqual(runtime_audit(self.root)['verified_successful_runtime_attempts'],0)

    def test_sidecars_count_toward_logical_storage_budget(self):
        self.store.max_logical_bytes=100
        with self.assertRaisesRegex(IntegrityError,'storage_budget'):self.store.receipt('1'*32,'prepared',{'input_ids':[1]*30})


if __name__=='__main__':unittest.main()
