"""Numeric metadata fixtures only; no queries, weights, vectors or MMD execution."""
import copy
from dataclasses import asdict, replace
import hashlib
import json
from pathlib import Path
import unittest

from stream_prada_order import deep_kernel_mmd_exporter as m
from stream_prada_order import cusum_curve_exporter as c
from stream_prada_order import hybrid_fusion as h
from stream_prada_order import hybrid_integration as a
from stream_prada_order.tests.test_cusum_curve_exporter import fixture as sequential_fixture, encoded, record
from stream_prada_order.tests.test_hybrid_integration import fixture as integration_fixture, payload, sha, PROFILE


def draw_fingerprint(rows):
    return h.fingerprint([{k: row[k] for k in ('start', 'end', 'reference_draws')} for row in rows])


def fixture(chronology='fixed_query_replay'):
    seq = sequential_fixture(chronology=chronology)
    manifest = seq['manifest']; reference = integration_fixture()[3]
    records = seq['evidence_records']
    definition = m.DeepKernelDefinition(
        source_revision=sha(8101), protocol_lock_sha256=sha(8102), input_dim=2, hidden_dim=128,
        feature_dim=64, base_bandwidth=1., feature_bandwidth=.5, epsilon=.1, dtype='float64',
        reference_repeats=1, reference_manifest_sha256=h.fingerprint(reference),
        training_provenance_sha256=record(records, 8103), selection_provenance_sha256=record(records, 8104),
        scoring_configuration_sha256=record(records, 8113))
    checkpoint = m.CheckpointEvidence('8105', sha(8106), definition, 'mea-detection-deep-v1', True, False,
                                      record(records, 8107))
    revision = h.DetectorRevision(definition.source_revision, checkpoint.checkpoint_sha256,
        m.configuration_fingerprint(definition), definition.selection_provenance_sha256)
    rows = payload('mmd_windows', manifest, reference)['rows']
    raw = encoded(rows); digest = hashlib.sha256(raw).hexdigest()
    evidence = m.MMDScoreEvidence(digest, h.fingerprint(manifest), h.fingerprint(seq['embedding_index']),
        revision, definition, h.fingerprint(reference), draw_fingerprint(rows), record(records, 8108), record(records, 8109))
    ref_evidence = m.ReferenceEvidence(h.fingerprint(reference), reference['embedding_artifact_sha256'],
        a.embedding_contract(manifest['representation']), len(reference['rows']), 'contiguous-little-endian',
        True, record(records, 8110), record(records, 8111))
    availability = m.AvailabilityEvidence(digest, h.fingerprint(manifest),
        'observed_query_position' if chronology == 'native' else 'declared_fixed_replay',
        tuple((r['start'], r['end'], r['available_at']) for r in rows), record(records, 8112))
    args = {k: seq[k] for k in ('manifest', 'certificate', 'embedding_index', 'expected_representation',
                               'source_evidence', 'evidence_records', 'profile')}
    args.update(raw_scores=raw, reference=reference, expected_definition=definition, expected_revision=revision,
        score_evidence=evidence, checkpoint_evidence=checkpoint, reference_evidence=ref_evidence,
        availability_evidence=availability)
    return args, seq


def changed_rows(args, mutate, *, rebind_draws=True, rebind_availability=True):
    rows = json.loads(args['raw_scores']); mutate(rows)
    args['raw_scores'] = encoded(rows); digest = hashlib.sha256(args['raw_scores']).hexdigest()
    args['score_evidence'] = replace(args['score_evidence'], score_sha256=digest,
        draws_sha256=draw_fingerprint(rows) if rebind_draws else args['score_evidence'].draws_sha256)
    args['availability_evidence'] = replace(args['availability_evidence'], score_sha256=digest,
        window_availability=tuple((r['start'], r['end'], r['available_at']) for r in rows)
        if rebind_availability else args['availability_evidence'].window_availability)


def aligned(args, seq, exported):
    sequential = c.export_cusum_curve(**seq)
    return a.align_exports(seq['manifest'], args['manifest'], args['certificate'], seq['embedding_index'],
        args['embedding_index'], sequential, exported, seq['expected_revision'], args['expected_revision'],
        args['reference'], args['profile'])


class DeepKernelExportTests(unittest.TestCase):
    def test_complete_export_uses_existing_wire_schema_and_preserves_inputs(self):
        args, _ = fixture(); before = copy.deepcopy(args)
        result = m.export_deep_kernel_mmd(**args)
        self.assertEqual(set(result), set(a.PAYLOAD_KEYS))
        self.assertEqual(result['schema_version'], 'hybrid-producer-scores-v1')
        self.assertEqual(result['kind'], 'mmd_windows')
        self.assertEqual(result['revision'], asdict(args['expected_revision']))
        self.assertEqual(result['rows'], json.loads(args['raw_scores']))
        self.assertEqual(args, before)
        result['rows'][0]['reference_draws'][0][0] = 99
        self.assertEqual(args, before)

    def test_task03_compatibility_exact_common_stream_windows_and_independent_revisions(self):
        args, seq = fixture(); points = aligned(args, seq, m.export_deep_kernel_mmd(**args)).points
        self.assertEqual([p.query_index for p in points], [150, 200, 250])
        self.assertTrue(all(p.sequential_valid and p.mmd_valid for p in points))
        self.assertEqual([p.mmd for p in points], [-.1, -.1, -.1])
        self.assertEqual(args['manifest'], seq['manifest'])
        self.assertNotEqual(args['expected_revision'], seq['expected_revision'])
        self.assertNotEqual(args['expected_revision'].model_revision, seq['expected_revision'].model_revision)
        self.assertEqual([(r['start'], r['end']) for r in m.export_deep_kernel_mmd(**args)['rows']],
                         [(1, 100), (51, 150), (101, 200), (151, 250)])

    def test_grid_window100_optional_and_never_a_joint_checkpoint(self):
        args, seq = fixture(); changed_rows(args, lambda rows: rows.pop(0))
        result = m.export_deep_kernel_mmd(**args)
        self.assertEqual(len(result['rows']), 3)
        self.assertEqual([p.query_index for p in aligned(args, seq, result).points], [150, 200, 250])

    def test_wrong_manifest_query_order_or_window_membership(self):
        args, _ = fixture(); args['score_evidence'] = replace(args['score_evidence'], manifest_sha256=sha(999))
        with self.assertRaises(ValueError): m.export_deep_kernel_mmd(**args)
        args, _ = fixture(); args['manifest']['queries'].reverse()
        with self.assertRaises(ValueError): m.export_deep_kernel_mmd(**args)
        args, _ = fixture(); changed_rows(args, lambda rows: rows[1].update(query_slice_sha256=sha(999)))
        with self.assertRaises(ValueError): m.export_deep_kernel_mmd(**args)

    def test_wrong_encoder_and_embedding_identity(self):
        for field in ('encoder_revision', 'tokenizer_revision', 'preprocessing_sha256'):
            args, _ = fixture(); args['manifest']['representation'][field] = sha(999)
            with self.subTest(field=field), self.assertRaises(ValueError): m.export_deep_kernel_mmd(**args)
        args, _ = fixture(); args['embedding_index']['rows'][0]['embedding_row_sha256'] = sha(999)
        with self.assertRaises(ValueError): m.export_deep_kernel_mmd(**args)
        args, _ = fixture(); args['score_evidence'] = replace(args['score_evidence'], embedding_index_sha256=sha(999))
        with self.assertRaises(ValueError): m.export_deep_kernel_mmd(**args)

    def test_wrong_checkpoint_or_unfrozen_or_pilot_checkpoint(self):
        for change in ({'checkpoint_sha256': sha(999)}, {'eval_mode': False}, {'requires_grad': True},
                       {'format': 'pilot'}, {'checkpoint_identity': ''}, {'verification_record_sha256': sha(999)}):
            args, _ = fixture(); args['checkpoint_evidence'] = replace(args['checkpoint_evidence'], **change)
            with self.subTest(change=change), self.assertRaises(ValueError): m.export_deep_kernel_mmd(**args)
        args, _ = fixture(); args['checkpoint_evidence'] = None
        with self.assertRaises(ValueError): m.export_deep_kernel_mmd(**args)

    def test_wrong_kernel_architecture_or_configuration_revision(self):
        for changes in ({'epsilon': .2}, {'base_bandwidth': 2.}, {'feature_bandwidth': 2.},
                        {'hidden_dim': 32}, {'source_revision': sha(999)}, {'protocol_lock_sha256': sha(999)}):
            args, _ = fixture(); definition = replace(args['expected_definition'], **changes)
            args['checkpoint_evidence'] = replace(args['checkpoint_evidence'], definition=definition)
            with self.subTest(changes=changes), self.assertRaises(ValueError): m.export_deep_kernel_mmd(**args)
        args, _ = fixture(); revision = replace(args['expected_revision'], configuration_revision=sha(999))
        args['expected_revision'] = revision; args['score_evidence'] = replace(args['score_evidence'], revision=revision)
        with self.assertRaises(ValueError): m.export_deep_kernel_mmd(**args)

    def test_invalid_expected_method_parameters(self):
        for changes in ({'epsilon': float('nan')}, {'base_bandwidth': 0.}, {'input_dim': True},
                        {'hidden_dim': 0}, {'dtype': 'unknown'}, {'reference_repeats': True}):
            args, _ = fixture(); args['expected_definition'] = replace(args['expected_definition'], **changes)
            with self.subTest(changes=changes), self.assertRaises(ValueError): m.export_deep_kernel_mmd(**args)

    def test_missing_training_selection_or_score_provenance(self):
        for attr in ('training_provenance_sha256', 'selection_provenance_sha256', 'scoring_configuration_sha256'):
            args, _ = fixture(); del args['evidence_records'][getattr(args['expected_definition'], attr)]
            with self.subTest(attr=attr), self.assertRaises(ValueError): m.export_deep_kernel_mmd(**args)
        args, _ = fixture(); del args['evidence_records'][args['score_evidence'].provenance_record_sha256]
        with self.assertRaises(ValueError): m.export_deep_kernel_mmd(**args)

    def test_missing_unfrozen_or_contaminated_reference_evidence(self):
        for change in ({'frozen': False}, {'row_count': 99}, {'layout': 'unknown'},
                       {'embedding_artifact_sha256': sha(999)}, {'reference_manifest_sha256': sha(999)},
                       {'physical_record_sha256': sha(999)}):
            args, _ = fixture(); args['reference_evidence'] = replace(args['reference_evidence'], **change)
            with self.subTest(change=change), self.assertRaises(ValueError): m.export_deep_kernel_mmd(**args)
        args, _ = fixture(); args['reference_evidence'] = None
        with self.assertRaises(ValueError): m.export_deep_kernel_mmd(**args)
        args, _ = fixture(); args['reference']['rows'][0]['text_sha256'] = args['manifest']['queries'][0]['text_sha256']
        with self.assertRaises(ValueError): m.export_deep_kernel_mmd(**args)
        args, _ = fixture(); args['reference']['rows'][0]['source_group_sha256'] = args['manifest']['queries'][0]['source_group_sha256']
        with self.assertRaises(ValueError): m.export_deep_kernel_mmd(**args)

    def test_incorrect_reference_draws_or_repetitions(self):
        for draws in (None, [[0] * 100], [list(range(99))], [list(range(99)) + [100]],
                      [list(range(100)), list(range(100))]):
            args, _ = fixture(); changed_rows(args, lambda rows: rows[1].update(reference_draws=draws))
            with self.subTest(draws_count=None if draws is None else len(draws)), self.assertRaises(ValueError):
                m.export_deep_kernel_mmd(**args)
        args, _ = fixture(); changed_rows(args, lambda rows: rows[1]['reference_draws'][0].reverse(), rebind_draws=False)
        with self.assertRaises(ValueError): m.export_deep_kernel_mmd(**args)
        args, _ = fixture(); del args['evidence_records'][args['score_evidence'].draws_record_sha256]
        with self.assertRaises(ValueError): m.export_deep_kernel_mmd(**args)

    def test_multiple_explicit_reference_repeats_are_passed_through(self):
        args, seq = fixture(); definition = replace(args['expected_definition'], reference_repeats=2)
        revision = replace(args['expected_revision'], configuration_revision=m.configuration_fingerprint(definition))
        args.update(expected_definition=definition, expected_revision=revision)
        args['checkpoint_evidence'] = replace(args['checkpoint_evidence'], definition=definition)
        args['score_evidence'] = replace(args['score_evidence'], definition=definition, revision=revision)
        changed_rows(args, lambda rows: [r['reference_draws'].append(list(reversed(range(100)))) for r in rows])
        result = m.export_deep_kernel_mmd(**args)
        self.assertEqual(result['reference_repeats'], 2)
        self.assertTrue(all(len(row['reference_draws']) == 2 for row in result['rows']))
        self.assertEqual([p.mmd for p in aligned(args, seq, result).points], [-.1, -.1, -.1])

    def test_duplicate_offgrid_wrong_size_and_terminal256_rejected(self):
        for mutate in (lambda rows: rows.append(copy.deepcopy(rows[1])),
                       lambda rows: rows[1].update(start=50),
                       lambda rows: rows[-1].update(start=157, end=256, computed_through=256, available_at=256)):
            args, _ = fixture(); changed_rows(args, mutate)
            with self.assertRaises(ValueError): m.export_deep_kernel_mmd(**args)

    def test_negative_finite_signed_scores_never_clipped_or_transformed(self):
        args, seq = fixture(); changed_rows(args, lambda rows: rows[1].update(value=-12.25))
        result = m.export_deep_kernel_mmd(**args)
        self.assertEqual(result['rows'][1]['value'], -12.25)
        self.assertEqual(aligned(args, seq, result).points[0].mmd, -12.25)

    def test_invalid_null_is_preserved_and_never_backfilled(self):
        args, seq = fixture(); changed_rows(args, lambda rows: rows[2].update(value=None, valid=False, reference_draws=None))
        result = m.export_deep_kernel_mmd(**args); point = aligned(args, seq, result).points[1]
        self.assertIsNone(result['rows'][2]['value']); self.assertFalse(result['rows'][2]['valid'])
        self.assertIsNone(point.mmd); self.assertEqual(point.mmd_reason, 'invalid')

    def test_nonfinite_bool_and_invalid_value_mismatch_rejected(self):
        for change in ({'value': True}, {'value': None}, {'value': 0., 'valid': False}):
            args, _ = fixture(); changed_rows(args, lambda rows: rows[1].update(change))
            with self.assertRaises(ValueError): m.export_deep_kernel_mmd(**args)
        for value in (float('nan'), float('inf'), float('-inf')):
            args, _ = fixture(); rows = json.loads(args['raw_scores']); rows[1]['value'] = value
            args['raw_scores'] = json.dumps(rows).encode(); digest = hashlib.sha256(args['raw_scores']).hexdigest()
            args['score_evidence'] = replace(args['score_evidence'], score_sha256=digest)
            args['availability_evidence'] = replace(args['availability_evidence'], score_sha256=digest)
            with self.assertRaises(ValueError): m.export_deep_kernel_mmd(**args)

    def test_missing_required_window_is_unavailable_not_zero(self):
        args, seq = fixture(); changed_rows(args, lambda rows: rows.pop(2))
        with self.assertRaises(m.MMDWindowsUnavailable): m.export_deep_kernel_mmd(**args)
        # No rejected payload enters integration. Absence is missing, not score0.
        sequential = c.export_cusum_curve(**seq)
        stream = a.validate_manifest(seq['manifest'], seq['certificate'], seq['embedding_index'], PROFILE)
        scores = a.export_scores(sequential, seq['manifest'], seq['certificate'], seq['embedding_index'], seq['expected_revision'], PROFILE)
        spec = h.Spec(stream.context, a.adapted_revision(seq['expected_revision'], 'cusum_curve', PROFILE),
            args['expected_revision'], a.schedule(PROFILE))
        points = h.align(spec, stream, scores, ()).points
        self.assertTrue(all(p.mmd is None and p.mmd_reason == 'missing' for p in points))

    def test_late_availability_preserved_no_stale_carry_forward(self):
        args, seq = fixture(); changed_rows(args, lambda rows: rows[2].update(available_at=201))
        result = m.export_deep_kernel_mmd(**args); point = aligned(args, seq, result).points[1]
        self.assertEqual(result['rows'][2]['available_at'], 201)
        self.assertIsNone(point.mmd); self.assertEqual(point.mmd_reason, 'not_available')
        args, _ = fixture(); changed_rows(args, lambda rows: rows[2].update(available_at=201), rebind_availability=False)
        with self.assertRaises(ValueError): m.export_deep_kernel_mmd(**args)

    def test_future_implicit_dependency_or_backdating_rejected(self):
        for change in ({'computed_through': 256}, {'computed_through': None}, {'available_at': 149}):
            args, _ = fixture(); changed_rows(args, lambda rows: rows[1].update(change))
            with self.subTest(change=change), self.assertRaises(ValueError): m.export_deep_kernel_mmd(**args)

    def test_incomplete_or_tampered_score_evidence_and_summary_rejected(self):
        args, _ = fixture(); args['score_evidence'] = None
        with self.assertRaises(ValueError): m.export_deep_kernel_mmd(**args)
        args, _ = fixture(); args['raw_scores'] += b' '
        with self.assertRaises(ValueError): m.export_deep_kernel_mmd(**args)
        for summary in (None, {'batch_id': 1, 'score': 2.}, [], [3.]):
            args, _ = fixture()
            args['raw_scores'] = None if summary is None else encoded(summary)
            if args['raw_scores'] is not None:
                digest = hashlib.sha256(args['raw_scores']).hexdigest()
                args['score_evidence'] = replace(args['score_evidence'], score_sha256=digest)
                args['availability_evidence'] = replace(args['availability_evidence'], score_sha256=digest)
            with self.assertRaises(m.MMDWindowsUnavailable): m.export_deep_kernel_mmd(**args)

    def test_wrong_availability_evidence_or_replay_claim(self):
        for change in ({'basis': 'inferred'}, {'record_sha256': sha(999)}, {'manifest_sha256': sha(999)}):
            args, _ = fixture(); args['availability_evidence'] = replace(args['availability_evidence'], **change)
            with self.assertRaises(ValueError): m.export_deep_kernel_mmd(**args)
        args, _ = fixture(); args['availability_evidence'] = None
        with self.assertRaises(ValueError): m.export_deep_kernel_mmd(**args)

    def test_native_chronology_requires_observed_availability(self):
        args, seq = fixture('native')
        result = m.export_deep_kernel_mmd(**args)
        self.assertEqual(result['availability_basis'], 'observed_query_position')
        self.assertTrue(all(p.mmd_valid for p in aligned(args, seq, result).points))
        args['availability_evidence'] = replace(args['availability_evidence'], basis='declared_fixed_replay')
        with self.assertRaises(ValueError): m.export_deep_kernel_mmd(**args)

    def test_task03_independent_revision_mismatch_is_rejected(self):
        args, seq = fixture(); exported = m.export_deep_kernel_mmd(**args)
        seq['expected_revision'] = replace(seq['expected_revision'], detector_revision=sha(999))
        with self.assertRaises(ValueError): aligned(args, seq, exported)

    def test_no_mutation_of_original_detector_or_results(self):
        root = Path(__file__).resolve().parents[2]
        paths = ['pilot/deep_kernel_pilot.py', 'stream_prada_order/cusum_curve_exporter.py',
            'stream_prada_order/common_stream_producer.py', 'stream_prada_order/hybrid_integration.py',
            'stream_prada_order/hybrid_fusion.py', 'experiment_result/main/seed=42/MMD/model_leeching_bge_bs1500/metadata.json']
        def hashes(): return {p: hashlib.sha256((root / p).read_bytes()).hexdigest() for p in paths}
        before = hashes(); args, _ = fixture(); m.export_deep_kernel_mmd(**args)
        self.assertEqual(hashes(), before)


if __name__ == '__main__': unittest.main()
