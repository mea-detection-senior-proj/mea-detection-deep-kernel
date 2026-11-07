"""Policy checks on numeric mocks; no real grants, models or participant data."""
from pathlib import Path
import copy
import json
import sys
import tempfile
import unittest
from datetime import datetime,timezone

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from stream_prada_order.traffic_runtime.policy import profile, limits, validate_manifest_plan, load_grant, code_digest, claim_grant
from stream_prada_order.traffic_collection.schema import IntegrityError, ExecutionDisabled, canonical, digest
from phase_g_helpers import manifest
from phase_h_helpers import grant_files


def setup_plan(kind='mock'):
    cfg=manifest();cfg['traffic_kind']=kind;cfg['victim']=profile()['identity']
    cfg['budget'].update(max_requests=4,max_attempts=4,max_attempts_per_request=1,
                         max_session_attempts=4,max_query_bytes=65536,max_response_bytes=16384,
                         max_logical_storage_bytes=4194304)
    plan={'schema_version':'qwen-query-plan-v1','run_id':cfg['run_id'],
          'session_id':'s1','native_session_sha256':digest('7'),
          'queries':[{'request_id':'q1','query_sha256':digest('1 2'),
                      'document_ids':['doc1'],'task_id':'task1','format_class':'other'}]}
    return cfg,plan


class PolicyTests(unittest.TestCase):
    def test_four_request_plan_is_explicit_benign_and_bounded(self):
        cfg,plan=setup_plan();validate_manifest_plan(cfg,plan)
        self.assertEqual(limits()['max_requests'],4)
        for field,value in [('label','attack'),('traffic_kind','unspecified')]:
            changed=copy.deepcopy(cfg);changed[field]=value
            with self.assertRaises(IntegrityError):validate_manifest_plan(changed,plan)

    def test_expanded_or_duplicate_plan_is_rejected(self):
        cfg,plan=setup_plan();plan['queries']*=5
        with self.assertRaises(IntegrityError):validate_manifest_plan(cfg,plan)

    def test_no_grant_is_not_execution_authorization(self):
        with self.assertRaises(ExecutionDisabled):load_grant(None,None,None,None)

    def test_generation_and_template_are_frozen_and_not_upstream_sampling(self):
        p=profile();self.assertFalse(p['generation']['do_sample'])
        self.assertEqual(p['chat_template_sha256'],digest(p['chat_template']))
        self.assertEqual(p['generation']['max_new_tokens'],128)
        self.assertEqual(len(code_digest()),64)

    def test_hash_bound_grant_and_expiry_are_checked(self):
        cfg,plan=setup_plan()
        with tempfile.TemporaryDirectory() as folder:
            path,sha,evidence,record=grant_files(folder,cfg,plan)
            now=datetime(2026,1,1,0,30,tzinfo=timezone.utc)
            grant=load_grant(path,sha,cfg,plan,evidence,now=now)
            self.assertEqual(grant.record['traffic_kind'],'mock')
            with self.assertRaisesRegex(IntegrityError,'expired'):
                load_grant(path,sha,cfg,plan,evidence,now=datetime(2026,1,2,tzinfo=timezone.utc))
            changed=copy.deepcopy(plan);changed['queries'][0]['query_sha256']=digest('2')
            with self.assertRaisesRegex(IntegrityError,'binding_mismatch'):
                load_grant(path,sha,cfg,changed,evidence,now=now)

    def test_grant_requires_evidence_and_exact_hash(self):
        cfg,plan=setup_plan()
        with tempfile.TemporaryDirectory() as folder:
            path,sha,evidence,record=grant_files(folder,cfg,plan)
            with self.assertRaisesRegex(IntegrityError,'hash_mismatch'):load_grant(path,'0'*64,cfg,plan,evidence)
            (evidence/(record['evidence']['privacy_review']+'.private')).write_bytes(b'8')
            with self.assertRaisesRegex(IntegrityError,'evidence_mismatch'):load_grant(path,sha,cfg,plan,evidence)

    def test_mock_grant_cannot_authorize_real_manifest(self):
        cfg,plan=setup_plan()
        with tempfile.TemporaryDirectory() as folder:
            path,sha,evidence,record=grant_files(folder,cfg,plan)
            cfg['traffic_kind']='real'
            with self.assertRaisesRegex(IntegrityError,'mock_real_mismatch'):load_grant(path,sha,cfg,plan,evidence)

    def test_one_shot_grant_cannot_reset_budget_by_changing_store(self):
        cfg,plan=setup_plan()
        with tempfile.TemporaryDirectory() as folder:
            path,sha,evidence,record=grant_files(folder,cfg,plan)
            grant=load_grant(path,sha,cfg,plan,evidence,now=datetime(2026,1,1,0,30,tzinfo=timezone.utc))
            registry=Path(folder)/'registry'
            claim_grant(grant,Path(folder)/'store1',registry=registry)
            with self.assertRaisesRegex(IntegrityError,'already_claimed'):claim_grant(grant,Path(folder)/'store2',registry=registry)
            with self.assertRaisesRegex(IntegrityError,'owner_mismatch'):claim_grant(grant,Path(folder)/'store2',registry=registry,worker_start=True)
            claim_grant(grant,Path(folder)/'store1',registry=registry,worker_start=True)
            with self.assertRaisesRegex(IntegrityError,'already_claimed'):claim_grant(grant,Path(folder)/'store1',registry=registry,worker_start=True)


if __name__=='__main__':unittest.main()
