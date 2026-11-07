"""Behavioral collector tests on mock numeric traffic only."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from phase_g_helpers import Clock, MockAdapter, digest, manifest
from traffic_collection.adapters import AdapterFailure, AdapterResponse, QwenLocalAdapter
from traffic_collection.collector import Collector, recover
from traffic_collection.schema import IntegrityError, ExecutionDisabled, validate_manifest
from traffic_collection.store import EventStore, read_events


class CollectorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / "private"
        self.store = EventStore(self.root, clock=Clock())

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def start(self, adapter=None, config=None):
        adapter = adapter or MockAdapter()
        collector = Collector(self.store, config or manifest(), adapter)
        collector.open_session("session1", digest("7"))
        return collector, adapter

    def test_success_preserves_chronology_identity_hashes_and_usage(self):
        c, adapter = self.start()
        result = c.collect("session1", "q1", "1 2 3", ["doc1"], "task1", "question_only")
        events = self.store.events()
        self.assertEqual([e["event_sequence"] for e in events], list(range(1, len(events) + 1)))
        sent = next(e for e in events if e["kind"] == "attempt_started")
        got = next(e for e in events if e["kind"] == "attempt_succeeded")
        self.assertLess(sent["utc"], got["utc"])
        self.assertEqual(result["status"], "succeeded")
        self.assertEqual(got["data"]["input_tokens"], 3)
        self.assertEqual(got["data"]["response_sha256"], digest("4 5"))
        self.assertEqual(len(adapter.calls), 1)

    def test_label_comes_from_manifest_not_length_or_format(self):
        c, _ = self.start(config=manifest(label="attack"))
        c.collect("session1", "q1", "1", ["doc1"], "task1", "question_only")
        self.assertEqual(self.store.state.runs["run1"]["manifest"]["label"], "attack")

    def test_duplicate_request_id_rejected_without_second_adapter_call(self):
        c, adapter = self.start()
        c.collect("session1", "q1", "1", ["doc1"], "task1", "other")
        with self.assertRaises(IntegrityError):
            c.collect("session1", "q1", "2", ["doc1"], "task1", "other")
        self.assertEqual(len(adapter.calls), 1)

    def test_not_sent_failure_retries_with_distinct_attempts(self):
        adapter = MockAdapter(outcomes=[AdapterFailure("timeout", "not_sent", True)])
        c, _ = self.start(adapter)
        c.collect("session1", "q1", "1", ["doc1"], "task1", "other")
        attempts = [e for e in self.store.events() if e["kind"] == "attempt_started"]
        self.assertEqual([e["data"]["dispatch_sequence"] for e in attempts], [1, 2])
        self.assertNotEqual(attempts[0]["data"]["attempt_id"], attempts[1]["data"]["attempt_id"])

    def test_unknown_delivery_is_not_retried(self):
        c, adapter = self.start(MockAdapter(outcomes=[RuntimeError("99887766")]))
        result = c.collect("session1", "q1", "1", ["doc1"], "task1", "other")
        self.assertEqual(result["status"], "unknown")
        self.assertEqual(len(adapter.calls), 1)
        self.assertNotIn("99887766", json.dumps(self.store.events()))

    def test_real_collection_and_qwen_execution_are_disabled(self):
        config = manifest(); config["traffic_kind"] = "real"
        adapter = MockAdapter()
        with self.assertRaises(ExecutionDisabled):
            Collector(self.store, config, adapter)
        self.assertEqual(adapter.calls, [])
        self.assertEqual(QwenLocalAdapter().deployment_plan()["execution_enabled"], False)
        with self.assertRaises(ExecutionDisabled):
            QwenLocalAdapter().respond("1", {})

    def test_private_text_not_in_event_records(self):
        c, _ = self.start()
        c.collect("session1", "q1", "112233445566778899", ["doc1"], "task1", "other")
        self.assertNotIn("112233445566778899", json.dumps(self.store.events()))
        self.assertEqual(self.store.read_blob(digest("112233445566778899")), b"112233445566778899")

    def test_authorization_and_source_metadata_required(self):
        config = manifest(); del config["authorization"]
        with self.assertRaises(IntegrityError): validate_manifest(config)
        c, adapter = self.start()
        with self.assertRaises(IntegrityError):
            c.collect("session1", "q1", "1", ["missing"], "task1", "other")
        self.assertEqual(adapter.calls, [])
