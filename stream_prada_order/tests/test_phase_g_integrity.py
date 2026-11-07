"""Durability, privacy, schema and recovery tests; all traffic is numeric mock data."""
import contextlib
import copy
import io
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from phase_g_helpers import Clock, MockAdapter, digest, manifest
from traffic_collection import schema
from traffic_collection.__main__ import main
from traffic_collection.adapters import AdapterFailure, AdapterResponse
from traffic_collection.audit import audit
from traffic_collection.collector import Collector, recover
from traffic_collection.schema import IntegrityError, ExecutionDisabled
from traffic_collection.store import EventStore, check_private_root, read_events


class IntegrityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / "private"
        self.store = EventStore(self.root, clock=Clock())

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def start(self, config=None, adapter=None):
        adapter = adapter or MockAdapter()
        collector = Collector(self.store, config or manifest(), adapter)
        collector.open_session("s1", digest("77"))
        return collector, adapter

    def finish(self, collector):
        collector.close_session("s1"); collector.close_run()

    def test_single_writer_lock_and_reopen(self):
        with self.assertRaisesRegex(IntegrityError, "writer_already_active"):
            EventStore(self.root)
        self.store.close()
        self.store = EventStore(self.root)
        self.assertEqual(self.store.events(), [])

    def test_sql_update_and_delete_are_blocked(self):
        self.start()
        for statement in ["UPDATE events SET body='0'", "DELETE FROM events"]:
            with self.assertRaises(sqlite3.IntegrityError): self.store.conn.execute(statement)
        self.assertEqual(len(self.store.events()), 2)

    def test_hash_chain_detects_external_tampering(self):
        self.start()
        self.store.conn.execute("DROP TRIGGER events_no_update")
        self.store.conn.execute("UPDATE events SET event_sha256=? WHERE sequence=1", ("0"*64,))
        with self.assertRaisesRegex(IntegrityError, "journal_corrupt"): read_events(self.root)

    def test_failed_insert_rolls_back_state_and_journal(self):
        c, _ = self.start()
        before = self.store.events()
        self.store.conn.set_authorizer(lambda action,*_: sqlite3.SQLITE_DENY if action == sqlite3.SQLITE_INSERT else sqlite3.SQLITE_OK)
        with self.assertRaises(sqlite3.DatabaseError): c.close_session("s1")
        self.store.conn.set_authorizer(None)
        self.assertEqual(self.store.events(), before)
        self.assertFalse(self.store.state.sessions["s1"]["closed"])
        self.finish(c)

    def test_corrupt_private_blob_fails_without_overwrite(self):
        sha = self.store.write_blob(b"123")
        path = self.root / "blobs" / (sha+".private")
        path.write_bytes(b"456")  # Deliberate adversarial test, never a collector operation.
        with self.assertRaisesRegex(IntegrityError,"blob_corrupt"): self.store.write_blob(b"123")
        self.assertEqual(path.read_bytes(), b"456")

    def test_repository_payload_paths_must_be_ignored(self):
        base = Path(__file__).resolve().parents[1]
        with self.assertRaisesRegex(IntegrityError,"private_path_not_git_ignored"):
            check_private_root(base / "unignored-private-test")
        self.assertEqual(check_private_root(base/"traffic_local"/"unit-probe"),base/"traffic_local"/"unit-probe")

    def test_exact_blob_path_cannot_bypass_git_ignore_with_an_exception(self):
        repo=Path(self.temp.name)/'repo';repo.mkdir()
        subprocess.run(['git','init','--quiet',str(repo)],check=True,capture_output=True)
        raw=b'123';sha=schema.digest(raw)
        (repo/'.gitignore').write_text('private/**\n!private/blobs/\n!private/blobs/'+sha+'.private\n',encoding='utf-8')
        with EventStore(repo/'private') as store:
            with self.assertRaisesRegex(IntegrityError,'private_path_not_git_ignored'):
                store.write_blob(raw)
            self.assertFalse((repo/'private/blobs'/ (sha+'.private')).exists())

    def test_previously_tracked_blob_is_refused_even_after_ignore_rule(self):
        repo=Path(self.temp.name)/'repo';repo.mkdir()
        subprocess.run(['git','init','--quiet',str(repo)],check=True,capture_output=True)
        raw=b'123';sha=schema.digest(raw);root=repo/'private'
        (root/'blobs').mkdir(parents=True)
        path=root/'blobs'/(sha+'.private');path.write_bytes(raw)
        subprocess.run(['git','-C',str(repo),'add','--',path.relative_to(repo).as_posix()],check=True,capture_output=True)
        (repo/'.gitignore').write_text('private/**\n',encoding='utf-8')
        with EventStore(root) as store:
            with self.assertRaisesRegex(IntegrityError,'private_path_not_git_ignored'):
                store.write_blob(raw)
            self.assertEqual(path.read_bytes(),raw)

    def test_manifest_secret_or_unknown_field_is_rejected(self):
        config = manifest(); config["api_key"] = "11223344"
        with self.assertRaises(IntegrityError): schema.validate_manifest(config)
        self.assertEqual(self.store.events(), [])

    def test_attack_provenance_cannot_be_missing(self):
        config = manifest(label="attack"); config["acquisition"] = None
        with self.assertRaisesRegex(IntegrityError,"label_provenance_mismatch"): schema.validate_manifest(config)

    def test_duplicate_json_keys_are_rejected(self):
        with self.assertRaises(IntegrityError): schema.strict_json('{"run_id":"r1","run_id":"r2"}')

    def test_unknown_schema_version_is_rejected(self):
        config = manifest(); config["schema_version"] = "traffic-manifest-v99"
        with self.assertRaises(IntegrityError): schema.validate_manifest(config)

    def test_session_boundaries_are_not_merged(self):
        c, _ = self.start()
        with self.assertRaisesRegex(IntegrityError,"previous_session_not_closed"):
            c.open_session("s2",digest("8"))
        c.close_session("s1")
        with self.assertRaisesRegex(IntegrityError,"session_not_open"):
            c.collect("s1","q1","1",["doc1"],"task1","other")
        c.open_session("s2",digest("8"))
        c.collect("s2","q1","1",["doc1"],"task1","other")
        c.close_session("s2"); c.close_run()
        self.assertEqual([s["logical_requests"] for s in audit(self.root)["sessions"]], [0,1])

    def test_adapter_identity_and_mock_gate_are_rechecked_before_dispatch(self):
        c, adapter = self.start()
        adapter.is_mock = False
        with self.assertRaises(ExecutionDisabled):
            c.collect("s1","q1","1",["doc1"],"task1","other")
        self.assertEqual(adapter.calls, [])

    def test_accepted_failure_is_not_retried_and_is_an_exposure(self):
        c, adapter = self.start(adapter=MockAdapter(outcomes=[AdapterFailure("timeout","accepted",True)]))
        c.collect("s1","q1","1",["doc1"],"task1","other"); self.finish(c)
        report = audit(self.root)
        self.assertEqual(len(adapter.calls),1)
        self.assertEqual(report["sessions"][0]["accepted_exposures"],1)

    def test_unavailable_tokens_stay_null(self):
        c, _ = self.start(adapter=MockAdapter(outcomes=[AdapterResponse("2")]))
        c.collect("s1","q1","1",["doc1"],"task1","other"); self.finish(c)
        outcome = next(e for e in self.store.events() if e["kind"] == "attempt_succeeded")
        self.assertIsNone(outcome["data"]["input_tokens"])
        self.assertEqual(audit(self.root)["length_and_declared_format"]["benign"]["unknown_input_token_counts"],1)

    def test_invalid_boolean_token_count_is_logged_as_failure(self):
        c, _ = self.start(adapter=MockAdapter(outcomes=[AdapterResponse("2",True,1,"mock_reported")]))
        result = c.collect("s1","q1","1",["doc1"],"task1","other")
        self.assertEqual(result["status"],"failed")
        self.assertEqual(self.store.events()[-2]["data"]["code"],"invalid_response")

    def test_input_budget_stops_before_adapter(self):
        config = manifest(); config["budget"]["max_query_bytes"] = 1
        c, adapter = self.start(config=config)
        with self.assertRaisesRegex(IntegrityError,"input_budget_exhausted"):
            c.collect("s1","q1","12",["doc1"],"task1","other")
        self.assertEqual(adapter.calls,[])

    def test_request_and_attempt_budgets_include_retry_intentions(self):
        config = manifest(); config["budget"]["max_requests"] = 1; config["budget"]["max_attempts"] = 1
        c, adapter = self.start(config=config,adapter=MockAdapter(outcomes=[AdapterFailure("timeout","not_sent",True)]))
        c.collect("s1","q1","1",["doc1"],"task1","other")
        with self.assertRaises(IntegrityError): c.collect("s1","q2","1",["doc1"],"task1","other")
        self.assertEqual(len(adapter.calls),1)
        self.assertEqual(self.store.events()[-1]["data"]["reason"],"budget_exhausted")

    def test_response_dependency_requires_prior_success_and_private_decision(self):
        c, adapter = self.start(config=manifest(label="attack"))
        c.collect("s1","q1","1",["doc1"],"task1","other")
        previous = next(e["data"]["attempt_id"] for e in self.store.events() if e["kind"]=="attempt_succeeded")
        sha = self.store.write_blob(b"3")
        c.collect("s1","q2","2",["doc1"],"task1","other",{"sha256":sha,"based_on_attempt_ids":[previous]})
        self.assertEqual(adapter.calls[-1][1]["decision"]["based_on_attempt_ids"],[previous])
        with self.assertRaisesRegex(IntegrityError,"invalid_response_dependency"):
            c.collect("s1","q3","3",["doc1"],"task1","other",{"sha256":sha,"based_on_attempt_ids":["future"]})
        self.assertEqual(len(adapter.calls),2)

    def test_recovery_does_not_resend_unknown_attempt(self):
        c, adapter = self.start(adapter=MockAdapter(outcomes=[SystemExit(91)]))
        with self.assertRaises(SystemExit): c.collect("s1","q1","1",["doc1"],"task1","other")
        prefix = self.store.events()
        self.store.close(); self.store = EventStore(self.root,clock=Clock())
        result = recover(self.store)
        self.assertEqual(result["unknown_attempts"],1)
        self.assertEqual(self.store.events()[:len(prefix)],prefix)
        self.assertEqual(self.store.state.requests["q1"]["status"],"unknown")
        self.assertEqual(len(adapter.calls),1)
        self.assertEqual(sum(recover(self.store).values()),0)

    def test_recovery_finalizes_durable_success_without_resend(self):
        c, adapter = self.start()
        original = self.store.append
        def crash(kind,*args,**kwargs):
            if kind=="request_finished": raise SystemExit(92)
            return original(kind,*args,**kwargs)
        with patch.object(self.store,"append",side_effect=crash):
            with self.assertRaises(SystemExit): c.collect("s1","q1","1",["doc1"],"task1","other")
        self.assertEqual(recover(self.store)["unknown_attempts"],0)
        self.assertEqual(self.store.state.requests["q1"]["status"],"succeeded")
        self.assertEqual(len(adapter.calls),1)

    def test_wall_clock_rollback_is_flagged_not_rewritten(self):
        c, _ = self.start()
        old = self.store.state.last_utc
        self.store.clock=lambda: ("2025-01-01T00:00:00.000000Z",999999)
        c.close_session("s1")
        last=self.store.events()[-1]
        self.assertLess(last["utc"],old); self.assertTrue(last["utc_regressed"])

    def test_cli_errors_do_not_print_private_values_or_create_store(self):
        captured=io.StringIO()
        with contextlib.redirect_stdout(captured): result=main(["audit","--root",str(self.root/"11223344")])
        self.assertEqual(result,2);self.assertNotIn("11223344",captured.getvalue())
        self.assertFalse((self.root/"11223344").exists())

    def test_uncommitted_sqlite_transaction_is_recovered_after_process_exit(self):
        self.start(); before=self.store.events();self.store.close()
        package=Path(__file__).resolve().parents[1]
        script="import os,sys;from traffic_collection.store import EventStore;s=EventStore(sys.argv[1]);s.conn.execute('BEGIN IMMEDIATE');s.conn.execute('INSERT INTO events VALUES(99,?,?,?)',('0','0'*64,'1'*64));os._exit(73)"
        env=dict(os.environ,PYTHONPATH=str(package))
        child=subprocess.run([sys.executable,"-c",script,str(self.root)],env=env,capture_output=True,timeout=20)
        self.assertEqual(child.returncode,73)
        self.store=EventStore(self.root)
        self.assertEqual(self.store.events(),before)

    def test_offline_import_and_mock_collection_need_no_model_or_network_library(self):
        package=Path(__file__).resolve().parents[1]
        script="import sys;from traffic_collection.adapters import QwenLocalAdapter;from traffic_collection.store import EventStore;assert not {'torch','transformers','huggingface_hub','requests','urllib.request'} & set(sys.modules);assert not QwenLocalAdapter().deployment_plan()['execution_enabled']"
        child=subprocess.run([sys.executable,"-c",script],env=dict(os.environ,PYTHONPATH=str(package)),capture_output=True,timeout=20)
        self.assertEqual(child.returncode,0)

    def test_recovery_before_dispatch_does_not_invent_an_exposure(self):
        c, adapter = self.start(); original = self.store.append
        def crash(kind,*args,**kwargs):
            if kind == 'attempt_started': raise SystemExit(93)
            return original(kind,*args,**kwargs)
        with patch.object(self.store,'append',side_effect=crash):
            with self.assertRaises(SystemExit): c.collect('s1','q1','1',['doc1'],'task1','other')
        result=recover(self.store)
        self.assertEqual(result['unknown_attempts'],0)
        self.assertEqual(adapter.calls,[])
        self.assertEqual(audit(self.root)['sessions'][0]['accepted_exposures'],0)

    def test_reopen_retains_active_manifest_storage_cap(self):
        config=manifest();config['budget']['max_logical_storage_bytes']=100000
        self.start(config=config);self.store.close();self.store=EventStore(self.root)
        self.assertEqual(self.store.max_logical_bytes,100000)

    def test_adapter_revision_change_is_rejected_before_call(self):
        c, adapter=self.start();adapter.identity['model_revision']='9'*40
        with self.assertRaisesRegex(IntegrityError,'adapter_revision_mismatch'):
            c.collect('s1','q1','1',['doc1'],'task1','other')
        self.assertEqual(adapter.calls,[])

    def test_hmac_pseudonyms_are_namespaced_and_need_external_secret(self):
        key=b'1'*32
        a=schema.pseudonym(key,'actor','123')
        self.assertEqual(a,schema.pseudonym(key,'actor','123'))
        self.assertNotEqual(a,schema.pseudonym(key,'native_session','123'))
        with self.assertRaises(IntegrityError): schema.pseudonym(b'1','actor','123')

    def test_oversized_output_is_an_accepted_failed_attempt(self):
        config=manifest();config['budget']['max_response_bytes']=1
        c, adapter=self.start(config=config)
        row=c.collect('s1','q1','1',['doc1'],'task1','other')
        self.assertEqual(row['status'],'failed');self.assertEqual(len(adapter.calls),1)
        self.assertEqual(self.store.events()[-2]['data']['delivery'],'accepted')

    def test_no_nonfinite_json_or_duplicate_source_ids(self):
        with self.assertRaises(IntegrityError): schema.strict_json('{"v":NaN}')
        config=manifest();config['sources'].append(copy.deepcopy(config['sources'][0]))
        with self.assertRaises(IntegrityError): schema.validate_manifest(config)

    def test_request_sequences_replay_rejects_missing_event(self):
        from traffic_collection.state import replay
        c,_=self.start();c.collect('s1','q1','1',['doc1'],'task1','other')
        values=self.store.events()
        with self.assertRaises(IntegrityError): replay(values[:2]+values[3:])

    def test_validate_manifest_cli_never_prints_its_contents(self):
        path=Path(self.temp.name)/'manifest.json';path.write_text(json.dumps(manifest()),encoding='utf-8')
        captured=io.StringIO()
        with contextlib.redirect_stdout(captured): result=main(['validate-manifest','--path',str(path)])
        self.assertEqual(result,0)
        self.assertNotIn(manifest()['actor_sha256'],captured.getvalue())

    def test_concurrent_callers_are_serialized_into_dispatch_order(self):
        import concurrent.futures
        c, adapter=self.start()
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            futures=[pool.submit(c.collect,'s1','q'+str(i),str(i+1),['doc1'],'task1','other') for i in range(2)]
            for future in futures: self.assertEqual(future.result()['status'],'succeeded')
        events=self.store.events();sent=[e for e in events if e['kind']=='attempt_started']
        self.assertEqual([e['data']['dispatch_sequence'] for e in sent],[1,2])
        self.assertEqual([e['request_id'] for e in sent],[r[1]['request_id'] for r in adapter.calls])

    def test_empty_database_left_by_initialization_crash_can_be_initialized(self):
        self.store.close()
        other=Path(self.temp.name)/'empty';other.mkdir()
        conn=sqlite3.connect(other/'events.sqlite3');conn.execute('PRAGMA user_version=0');conn.close()
        self.assertGreater((other/'events.sqlite3').stat().st_size,0)
        with EventStore(other) as recovered: self.assertEqual(recovered.events(),[])

    def test_unrelated_database_is_never_initialized_or_overwritten(self):
        other=Path(self.temp.name)/'other';other.mkdir()
        conn=sqlite3.connect(other/'events.sqlite3');conn.execute('CREATE TABLE other(value)');conn.commit();conn.close()
        before=(other/'events.sqlite3').read_bytes()
        with self.assertRaises(IntegrityError): EventStore(other)
        self.assertEqual((other/'events.sqlite3').read_bytes(),before)

    def test_unicode_private_path_and_numeric_content_roundtrip(self):
        other=Path(self.temp.name)/'ไทย 123'
        with EventStore(other,clock=Clock()) as store:
            c=Collector(store,manifest(),MockAdapter());c.open_session('s1',digest('7'))
            c.collect('s1','q1','๑ ๒',['doc1'],'task1','other');c.close_session('s1');c.close_run()
            self.assertEqual(store.read_blob(digest('๑ ๒')).decode(),'๑ ๒')
            self.assertEqual(audit(other)['session_count'],1)
