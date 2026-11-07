"""Joined private metadata keeps unknown responses distinct from real responses."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from phase_g_helpers import Clock, MockAdapter, digest, manifest
from traffic_collection.adapters import AdapterFailure
from traffic_collection.collector import Collector, recover
from traffic_collection.store import EventStore
from traffic_collection.views import attempt_records
from traffic_collection.schema import IntegrityError
from traffic_collection.store import read_events


class ViewTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)/'private'
        self.store=EventStore(self.root,clock=Clock())

    def tearDown(self): self.store.close();self.temp.cleanup()

    def collect(self, outcomes=None):
        collector=Collector(self.store,manifest(),MockAdapter(outcomes=outcomes))
        collector.open_session('s1',digest('7'))
        collector.collect('s1','q1','112233445566778899',['doc1'],'task1','other')
        collector.close_session('s1');collector.close_run()
        return list(attempt_records(self.root))

    def test_success_has_joined_identity_timestamps_usage_and_no_raw_contents(self):
        rows=self.collect();row=rows[0]
        self.assertLess(row['request_utc'],row['response_utc'])
        self.assertEqual(row['victim'],manifest()['victim'])
        self.assertEqual(row['input_tokens'],3)
        self.assertEqual(row['source_documents'],manifest()['sources'])
        self.assertNotIn('112233445566778899',json.dumps(rows))
        self.assertIsNone(row['failure_observed_utc'])

    def test_failure_observation_is_not_fabricated_response_timestamp(self):
        row=self.collect([AdapterFailure('timeout','unknown',False)])[0]
        self.assertIsNone(row['response_utc']);self.assertIsNotNone(row['failure_observed_utc'])
        self.assertIsNone(row['input_tokens']);self.assertFalse(row['elapsed_is_response_latency'])

    def test_retry_view_preserves_both_attempts_and_link(self):
        rows=self.collect([AdapterFailure('timeout','not_sent',True)])
        self.assertEqual(len(rows),2)
        self.assertEqual(rows[1]['retry_of'],rows[0]['attempt_id'])
        self.assertEqual([r['dispatch_sequence'] for r in rows],[1,2])
        self.assertEqual([r['request_sequence'] for r in rows],[1,1])

    def test_recovery_time_is_not_a_response_or_cross_epoch_latency(self):
        c=Collector(self.store,manifest(),MockAdapter(outcomes=[SystemExit(91)]));c.open_session('s1',digest('7'))
        with self.assertRaises(SystemExit): c.collect('s1','q1','1',['doc1'],'task1','other')
        self.store.close();self.store=EventStore(self.root,clock=Clock());recover(self.store)
        row=list(attempt_records(self.root))[0]
        self.assertIsNone(row['response_utc']);self.assertIsNotNone(row['recovery_observed_utc'])
        self.assertIsNone(row['collector_elapsed_ns'])

    def test_joined_view_rejects_a_changing_snapshot(self):
        self.collect();events=read_events(self.root)
        with patch('traffic_collection.views.read_events',side_effect=[events,events[:-1]]):
            with self.assertRaisesRegex(IntegrityError,'concurrent_write_retry_audit'):
                list(attempt_records(self.root))
