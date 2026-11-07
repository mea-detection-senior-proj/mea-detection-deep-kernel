"""Dataset accounting on mocks: never interpret these fixtures as real cohorts."""
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from phase_g_helpers import Clock, MockAdapter, digest, manifest
from traffic_collection.audit import audit
from traffic_collection.adapters import AdapterFailure
from traffic_collection.collector import Collector, recover
from traffic_collection.store import EventStore


class AuditTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)/"private"
        self.store=EventStore(self.root,clock=Clock())

    def tearDown(self):
        self.store.close();self.temp.cleanup()

    def add_session(self, run, label, query, actor="1", source="2", split="development", count=1, format_class="other"):
        cfg=manifest(run,label,actor,source);cfg['split']=split
        c=Collector(self.store,cfg,MockAdapter());c.open_session(run+"s",digest(run))
        for n in range(count): c.collect(run+"s",run+"q"+str(n),query,["doc1"],"task1",format_class)
        c.close_session(run+"s");c.close_run()

    def test_lengths_q102_and_horizon256_are_per_native_session(self):
        cfg=manifest();cfg['budget']['max_requests']=1000;cfg['budget']['max_attempts']=1000
        c=Collector(self.store,cfg,MockAdapter())
        for sid,n in [('s1',101),('s2',102),('s3',256)]:
            c.open_session(sid,digest(sid))
            for i in range(n): c.collect(sid,sid+str(i),"1",["doc1"],"task1","other")
            c.close_session(sid)
        c.close_run();report=audit(self.root)
        self.assertEqual([r['accepted_exposures'] for r in report['sessions']],[101,102,256])
        self.assertEqual(report['eligible_sessions_q102'],2)
        self.assertEqual(report['sessions_supporting_horizon256'],1)
        self.assertEqual(report['components_with_horizon256_session'],1)
        self.assertEqual(report['evidence_kind'],'mock_only_not_research')
        self.assertEqual(report['real_horizon256_feasibility'],'unmeasured_no_real_data')
        self.assertIsNone(report['scientifically_verified_independent_sessions'])

    def test_two_short_sessions_are_never_concatenated(self):
        self.add_session('r1','benign','1',count=100)
        self.add_session('r2','benign','2',count=200)
        report=audit(self.root)
        self.assertEqual(report['sessions_supporting_horizon256'],0)

    def test_recovered_run_does_not_certify_a_previously_closed_session(self):
        c=Collector(self.store,manifest(),MockAdapter());c.open_session('s1',digest('7'))
        for n in range(102): c.collect('s1','q'+str(n),'1',['doc1'],'task1','other')
        c.close_session('s1')
        recover(self.store)  # Run interrupted after session close, before run close.
        report=audit(self.root)
        self.assertEqual(report['sessions'][0]['accepted_exposures'],102)
        self.assertFalse(report['sessions'][0]['eligible_q102'])
        self.assertEqual(report['eligible_sessions_q102'],0)

    def test_same_actor_links_otherwise_distinct_runs(self):
        self.add_session('r1','benign','1',source='2')
        self.add_session('r2','attack','2',source='3')
        self.assertEqual(audit(self.root)['operational_source_components'],1)

    def test_same_source_links_distinct_actors(self):
        self.add_session('r1','benign','1',actor='1')
        self.add_session('r2','attack','2',actor='9')
        self.assertEqual(audit(self.root)['operational_source_components'],1)

    def test_generic_format_does_not_link_independent_metadata_components(self):
        self.add_session('r1','benign','1',actor='1',source='2')
        self.add_session('r2','benign','2',actor='8',source='9')
        self.assertEqual(audit(self.root)['operational_source_components'],2)

    def test_normalized_duplicate_links_sessions_and_flags_cross_split_leakage(self):
        self.add_session('r1','benign','1  2',actor='1',source='2',split='fit')
        self.add_session('r2','attack','1 2',actor='8',source='9',split='final_test')
        report=audit(self.root)
        self.assertEqual(report['operational_source_components'],1)
        self.assertEqual(report['leakage_risks']['cross_split_components'],1)
        self.assertEqual(report['leakage_risks']['query_hashes_shared_across_labels'],1)
        self.assertFalse(report['research_data_ready'])

    def test_length_format_common_support_and_negative_findings(self):
        self.add_session('r1','benign','1',actor='1',source='2',format_class='question_only')
        self.add_session('r2','attack',' '.join(str(i) for i in range(140)),actor='8',source='9',format_class='context_request')
        report=audit(self.root)
        self.assertEqual(report['common_support']['status'],'no_observed_support')
        self.assertEqual(report['common_support']['unique_query_word_format_overlap_capacity'],0)
        self.assertEqual(report['length_and_declared_format']['attack']['word_bins'],[0,0,1,0])

    def test_overlap_is_not_claimed_to_be_whole_session_matching(self):
        self.add_session('r1','benign','1',actor='1',source='2')
        self.add_session('r2','attack','2',actor='8',source='9')
        report=audit(self.root)
        self.assertEqual(report['common_support']['unique_query_word_format_overlap_capacity'],1)
        self.assertEqual(report['common_support']['whole_matched_sessions_constructed'],0)
        self.assertEqual(report['common_support']['bge_pretruncation_tokens'],'unmeasured')

    def test_not_sent_retry_does_not_inflate_accepted_length(self):
        c=Collector(self.store,manifest(),MockAdapter(outcomes=[AdapterFailure('timeout','not_sent',True)]))
        c.open_session('s1',digest('7'));c.collect('s1','q1','1',['doc1'],'task1','other')
        c.close_session('s1');c.close_run();row=audit(self.root)['sessions'][0]
        self.assertEqual(row['logical_requests'],1)
        self.assertEqual(row['accepted_exposures'],1)
        self.assertEqual(row['not_sent_attempts'],1)

    def test_orphan_blob_is_reported_and_not_deleted(self):
        sha=self.store.write_blob(b'123');report=audit(self.root)
        self.assertEqual(report['unreferenced_blob_files'],1)
        self.assertEqual(self.store.read_blob(sha),b'123')

    def test_actual_multiline_signal_is_separate_from_declared_format_and_label(self):
        self.add_session('r1','benign','1\n2',format_class='question_only')
        result=audit(self.root)
        self.assertEqual(result['observed_lexical_format_signals']['benign']['multiline'],1)
        self.assertEqual(result['length_and_declared_format']['benign']['format_counts'],{'question_only':1})

    def test_shared_attack_lineage_links_distinct_actor_source_runs(self):
        for n in [1,2]:
            cfg=manifest('r'+str(n),'attack',actor=str(n),source=str(n+10))
            cfg['acquisition']['lineage_sha256']=digest('shared-lineage')
            c=Collector(self.store,cfg,MockAdapter());sid='s'+str(n);c.open_session(sid,digest(sid))
            c.collect(sid,'q'+str(n),str(n),['doc1'],'task1','other');c.close_session(sid);c.close_run()
        self.assertEqual(audit(self.root)['operational_source_components'],1)

    def test_unknown_delivery_blocks_session_eligibility(self):
        c=Collector(self.store,manifest(),MockAdapter(outcomes=[AdapterFailure('timeout','unknown',True)]))
        c.open_session('s1',digest('7'));c.collect('s1','q1','1',['doc1'],'task1','other')
        c.close_session('s1');c.close_run();row=audit(self.root)['sessions'][0]
        self.assertEqual(row['unknown_dispatches'],1);self.assertFalse(row['eligible_q102'])

    def test_idle_gap_is_flagged_without_inventing_a_new_session(self):
        c=Collector(self.store,manifest(),MockAdapter());c.open_session('s1',digest('7'))
        c.collect('s1','q1','1',['doc1'],'task1','other')
        self.store.clock=lambda: ('2026-01-01T01:00:00.000000Z',3600*10**9)
        c.collect('s1','q2','2',['doc1'],'task1','other');c.close_session('s1');c.close_run()
        report=audit(self.root)
        self.assertEqual(report['session_count'],1)
        self.assertTrue(report['sessions'][0]['idle_gap_exceeded'])
