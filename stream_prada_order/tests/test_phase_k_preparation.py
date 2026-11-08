"""Preparation tests only. No requests, model imports or fabricated grants."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
from stream_prada_order.traffic_collection.schema import IntegrityError, validate_manifest
from stream_prada_order.traffic_runtime.policy import limits, profile, validate_manifest_plan

SOURCE=Path(__file__).resolve().parents[1]/'phase_k_prepare.py'
spec=importlib.util.spec_from_file_location('phase_k_prepare',SOURCE)
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

class PreparationTests(unittest.TestCase):
    def test_draft_cannot_be_used_as_execution_manifest(self):
        docs=m.preparation_documents('1'*40)
        self.assertFalse(docs['manifest']['execution_authorized'])
        with self.assertRaises(IntegrityError):validate_manifest(docs['manifest'])
        with self.assertRaises(IntegrityError):validate_manifest(docs['manifest']['document'])

    def test_no_queries_hashes_sessions_or_approvals_are_invented(self):
        docs=m.preparation_documents('1'*40)
        cfg=docs['manifest']['document'];p=docs['query_plan']['document']
        for k in ['run_id','collector_revision','actor_sha256','source_group_sha256','protocol_sha256','sources','task_ids']:
            self.assertIsNone(cfg[k])
        self.assertIsNone(cfg['authorization']['evidence_sha256'])
        self.assertIsNone(p['queries']);self.assertIsNone(p['native_session_sha256'])
        self.assertIsNone(docs['requirements']['grant_sha256'])

    def test_limits_identity_and_retry_policy_stay_frozen(self):
        before=profile();docs=m.preparation_documents('1'*40)
        cfg=docs['manifest']['document']
        self.assertEqual(cfg['victim'],before['identity'])
        self.assertEqual(docs['requirements']['limits'],limits())
        self.assertEqual(cfg['budget']['max_attempts_per_request'],1)
        self.assertEqual(cfg['budget']['max_requests'],4)
        self.assertEqual(cfg['retry_policy'],'not_sent_only')
        self.assertIsNone(cfg['acquisition']);self.assertEqual(profile(),before)

    def test_mutating_draft_does_not_change_frozen_profile(self):
        docs=m.preparation_documents('1'*40);docs['manifest']['document']['victim']['model_id']='1'
        self.assertEqual(profile()['identity']['model_id'],'Qwen/Qwen2.5-1.5B-Instruct')

    def test_invalid_preparation_head_is_rejected(self):
        for head in ['main','1'*39,'Z'*40]:
            with self.assertRaises(ValueError):m.preparation_documents(head)

    def test_missing_approval_is_refused_without_claim(self):
        with tempfile.TemporaryDirectory() as folder:
            result=m.approval_refusals(None)
            self.assertTrue(result['missing_grant_refused'])
            self.assertFalse(result['claim_created']);self.assertFalse(list(Path(folder).iterdir()))

    def test_acquisition_record_never_becomes_inference_grant(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'1.json';p.write_text('{"approved":true,"acquisition_only":true}')
            result=m.approval_refusals(p)
            self.assertTrue(result['acquisition_grant_refused']);self.assertFalse(result['claim_created'])
            self.assertEqual(len(list(Path(folder).iterdir())),1)

if __name__=='__main__':unittest.main(verbosity=2)
