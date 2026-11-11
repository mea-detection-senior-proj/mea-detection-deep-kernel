"""Synthetic numeric records only; never execute PRADA/CUSUM/model algorithms."""
import copy
from dataclasses import asdict, replace
import hashlib
import json
from pathlib import Path
import unittest

from stream_prada_order import cusum_curve_exporter as c
from stream_prada_order import hybrid_fusion as h
from stream_prada_order import hybrid_integration as a
from stream_prada_order import common_stream_producer as common
from stream_prada_order.tests.test_common_stream_producer import inputs as common_inputs, rebind_order
from stream_prada_order.tests.test_hybrid_integration import payload, sha, PROFILE


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def record(records, value):
    raw = encoded(value)
    digest = hashlib.sha256(raw).hexdigest()
    records[digest] = raw
    return digest


def fixture(direction='lower', k=.5, repeated=False, chronology='fixed_query_replay'):
    source = common_inputs(chronology)
    if repeated:
        for key in ('text_sha256', 'embedding_row', 'embedding_row_sha256'):
            source['ordered_requests'][1][key] = source['ordered_requests'][0][key]
        rebind_order(source)
    manifest = common.produce_manifest(**source)
    rows = payload('cusum_curve', manifest)['rows']
    # Deliberately nonmonotonic fixtures distinguish current score from maxima.
    for row in rows: row['value'] = float(row['end'] % 9)
    rows[149-102]['value'] = 999.
    records = source['evidence_records']
    fit = {'fit_cohorts': [0, 1], 'sigma_floor': .01, 'mu': [1.] * 255, 'sigma': [.1] * 255}
    definition = c.CusumDefinition(direction, k, record(records, fit),
                                   record(records, 7101), record(records, 7102))
    revision = h.DetectorRevision(sha(7103), definition.fit_parameters_sha256,
                                   c.configuration_fingerprint(definition), definition.fit_provenance_sha256)
    raw = encoded(rows); curve_sha = hashlib.sha256(raw).hexdigest()
    binding = c.CurveEvidence(curve_sha, h.fingerprint(manifest), h.fingerprint(source['embedding_index']),
                              revision, definition, record(records, 7104))
    availability = c.AvailabilityEvidence(curve_sha, h.fingerprint(manifest),
        'observed_query_position' if chronology == 'native' else 'declared_fixed_replay',
        tuple((r['end'], r['available_at']) for r in rows), record(records, 7105))
    return dict(raw_curve=raw, manifest=manifest, certificate=source['certificate'],
                embedding_index=source['embedding_index'], expected_representation=source['expected_representation'],
                source_evidence=source['evidence'], evidence_records=records, profile=PROFILE,
                expected_revision=revision, expected_definition=definition,
                curve_evidence=binding, availability_evidence=availability)


def changed_rows(args, mutate, *, update_availability=True):
    rows = json.loads(args['raw_curve']); mutate(rows)
    args['raw_curve'] = encoded(rows)
    digest = hashlib.sha256(args['raw_curve']).hexdigest()
    args['curve_evidence'] = replace(args['curve_evidence'], curve_sha256=digest)
    args['availability_evidence'] = replace(args['availability_evidence'], curve_sha256=digest,
        query_availability=tuple((r['end'], r['available_at']) for r in rows)
        if update_availability else args['availability_evidence'].query_availability)


def aligned(args, exported):
    stream = a.validate_manifest(args['manifest'], args['certificate'], args['embedding_index'], args['profile'])
    scores = a.export_scores(exported, args['manifest'], args['certificate'], args['embedding_index'],
                             args['expected_revision'], args['profile'])
    spec = h.Spec(stream.context, a.adapted_revision(args['expected_revision'], 'cusum_curve', args['profile']),
                  args['expected_revision'], a.schedule(args['profile']))
    return h.align(spec, stream, scores, ())


class CurveExporterTests(unittest.TestCase):
    def test_complete_curve_is_existing_payload_preserving_exact_values(self):
        args = fixture(); before = copy.deepcopy(args)
        result = c.export_cusum_curve(**args)
        self.assertEqual(set(result), set(a.PAYLOAD_KEYS))
        self.assertEqual(result['schema_version'], 'hybrid-producer-scores-v1')
        self.assertEqual(result['kind'], 'cusum_curve')
        self.assertEqual(result['rows'], json.loads(args['raw_curve']))
        self.assertEqual([r['end'] for r in result['rows']], list(range(102, 257)))
        self.assertEqual(result['revision'], asdict(args['expected_revision']))
        self.assertEqual(args, before)
        result['rows'][0]['value'] = 55.
        self.assertEqual(args, before)

    def test_exact_joint_checkpoints_use_current_values_not_maximum_or_latch(self):
        args = fixture(); points = aligned(args, c.export_cusum_curve(**args)).points
        self.assertEqual([p.query_index for p in points], [150, 200, 250])
        self.assertEqual([p.sequential for p in points], [float(t % 9) for t in (150, 200, 250)])
        self.assertTrue(all(p.sequential_reason == 'valid' for p in points))
        self.assertNotEqual(points[0].sequential, 999.)

    def test_wrong_manifest_and_embedding_index_hash(self):
        for field in ('manifest_sha256', 'embedding_index_sha256'):
            args = fixture(); args['curve_evidence'] = replace(args['curve_evidence'], **{field: sha(999)})
            with self.subTest(field=field), self.assertRaises(ValueError): c.export_cusum_curve(**args)

    def test_wrong_request_order_or_embedding_identity(self):
        args = fixture(); args['manifest']['queries'].reverse()
        with self.assertRaises(ValueError): c.export_cusum_curve(**args)
        args = fixture(); args['embedding_index']['rows'][0]['embedding_row_sha256'] = sha(999)
        with self.assertRaises(ValueError): c.export_cusum_curve(**args)
        args = fixture(); args['manifest']['representation']['encoder_revision'] = sha(999)
        with self.assertRaises(ValueError): c.export_cusum_curve(**args)

    def test_missing_or_incomplete_curve_is_unavailable_not_imputed(self):
        args = fixture(); args['raw_curve'] = None
        with self.assertRaises(c.CurveUnavailable): c.export_cusum_curve(**args)
        for position in (0, 150-102, -1):
            args = fixture(); changed_rows(args, lambda rows: rows.pop(position))
            with self.subTest(position=position), self.assertRaises(c.CurveUnavailable): c.export_cusum_curve(**args)

    def test_duplicate_or_reordered_curve_positions_rejected(self):
        for mutate in (lambda rows: rows.append(copy.deepcopy(rows[0])), lambda rows: rows.reverse()):
            args = fixture(); changed_rows(args, mutate)
            with self.assertRaises(ValueError): c.export_cusum_curve(**args)

    def test_invalid_score_preserved_and_marked_unavailable_at_checkpoint(self):
        args = fixture(); changed_rows(args, lambda rows: rows[150-102].update(value=None, valid=False))
        result = c.export_cusum_curve(**args); point = aligned(args, result).points[0]
        self.assertIsNone(result['rows'][150-102]['value'])
        self.assertFalse(result['rows'][150-102]['valid'])
        self.assertIsNone(point.sequential); self.assertEqual(point.sequential_reason, 'invalid')

    def test_nonfinite_negative_or_validity_inconsistent_scores_rejected(self):
        for change in ({'value': -1.}, {'value': None}, {'value': True}, {'valid': False, 'value': 0.}):
            args = fixture(); changed_rows(args, lambda rows: rows[0].update(change))
            with self.subTest(change=change), self.assertRaises(ValueError): c.export_cusum_curve(**args)
        for value in (float('nan'), float('inf'), float('-inf')):
            args = fixture(); rows = json.loads(args['raw_curve']); rows[0]['value'] = value
            args['raw_curve'] = json.dumps(rows).encode()
            digest = hashlib.sha256(args['raw_curve']).hexdigest()
            args['curve_evidence'] = replace(args['curve_evidence'], curve_sha256=digest)
            args['availability_evidence'] = replace(args['availability_evidence'], curve_sha256=digest)
            with self.assertRaises(ValueError): c.export_cusum_curve(**args)

    def test_all_directions_and_k_alternatives_remain_explicit(self):
        for direction in ('upper', 'lower', 'two_sided'):
            for k in (.5, 1.):
                with self.subTest(direction=direction, k=k):
                    args = fixture(direction, k)
                    self.assertEqual(c.export_cusum_curve(**args)['revision']['configuration_revision'],
                                     c.configuration_fingerprint(args['expected_definition']))

    def test_direction_k_or_configuration_mismatch(self):
        for changes in ({'direction': 'upper'}, {'k': 1.}, {'direction': 'best'}, {'k': .25}, {'k': True}):
            args = fixture()
            args['curve_evidence'] = replace(args['curve_evidence'],
                definition=replace(args['expected_definition'], **changes))
            with self.subTest(changes=changes), self.assertRaises(ValueError): c.export_cusum_curve(**args)
        args = fixture(); args['expected_revision'] = replace(args['expected_revision'], configuration_revision=sha(99))
        args['curve_evidence'] = replace(args['curve_evidence'], revision=args['expected_revision'])
        with self.assertRaises(ValueError): c.export_cusum_curve(**args)

    def test_incorrect_detector_model_and_fit_provenance(self):
        for field in ('detector_revision', 'model_revision', 'calibration_provenance'):
            args = fixture(); args['curve_evidence'] = replace(args['curve_evidence'],
                revision=replace(args['expected_revision'], **{field: sha(99)}))
            with self.subTest(field=field), self.assertRaises(ValueError): c.export_cusum_curve(**args)
        args = fixture(); key = args['expected_definition'].fit_provenance_sha256
        del args['evidence_records'][key]
        with self.assertRaises(ValueError): c.export_cusum_curve(**args)
        args = fixture(); args['evidence_records'][args['expected_definition'].upstream_provenance_sha256] = b'999'
        with self.assertRaises(ValueError): c.export_cusum_curve(**args)

    def test_position_fit_artifact_requires_exact_hash_and_phase_d_shape(self):
        for mutate in (lambda f: f['mu'].pop(), lambda f: f['sigma'].pop(),
                       lambda f: f.update(sigma_floor=.1), lambda f: f['sigma'].__setitem__(0, 0.),
                       lambda f: f.update(fit_cohorts=[])):
            args = fixture(); fit = json.loads(args['evidence_records'][args['expected_definition'].fit_parameters_sha256])
            mutate(fit); fit_hash = record(args['evidence_records'], fit)
            definition = replace(args['expected_definition'], fit_parameters_sha256=fit_hash)
            revision = replace(args['expected_revision'], model_revision=fit_hash,
                               configuration_revision=c.configuration_fingerprint(definition))
            args.update(expected_definition=definition, expected_revision=revision)
            args['curve_evidence'] = replace(args['curve_evidence'], definition=definition, revision=revision)
            with self.assertRaises(ValueError): c.export_cusum_curve(**args)

    def test_future_dependency_and_backdating_rejected(self):
        for change in ({'computed_through': 256}, {'computed_through': None}, {'available_at': 149}):
            args = fixture(); changed_rows(args, lambda rows: rows[150-102].update(change))
            with self.subTest(change=change), self.assertRaises(ValueError): c.export_cusum_curve(**args)

    def test_late_score_keeps_availability_and_never_carries_forward(self):
        args = fixture(); changed_rows(args, lambda rows: rows[200-102].update(available_at=201))
        result = c.export_cusum_curve(**args)
        self.assertEqual(result['rows'][200-102]['available_at'], 201)
        point = aligned(args, result).points[1]
        self.assertIsNone(point.sequential); self.assertEqual(point.sequential_reason, 'not_available')
        args = fixture(); changed_rows(args, lambda rows: rows[200-102].update(available_at=201), update_availability=False)
        with self.assertRaises(ValueError): c.export_cusum_curve(**args)

    def test_repeated_text_and_rows_have_distinct_unchanged_request_ids(self):
        args = fixture(repeated=True); result = c.export_cusum_curve(**args)
        self.assertEqual(len(result['rows']), 155)
        self.assertEqual([q['request_id'] for q in args['manifest']['queries'][:2]], ['1', '2'])
        args['manifest']['queries'][1]['request_id'] = '1'
        with self.assertRaises(ValueError): c.export_cusum_curve(**args)

    def test_missing_tampered_or_unbound_authentic_curve_evidence(self):
        args = fixture(); args['curve_evidence'] = None
        with self.assertRaises(ValueError): c.export_cusum_curve(**args)
        args = fixture(); args['raw_curve'] += b' '
        with self.assertRaises(ValueError): c.export_cusum_curve(**args)
        args = fixture(); del args['evidence_records'][args['curve_evidence'].provenance_record_sha256]
        with self.assertRaises(ValueError): c.export_cusum_curve(**args)

    def test_summary_only_inputs_are_unavailable(self):
        for summary in ({'max_score': 9., 'first_alert': 150}, [9.], [], {'rows': []}):
            args = fixture(); args['raw_curve'] = encoded(summary)
            digest = hashlib.sha256(args['raw_curve']).hexdigest()
            args['curve_evidence'] = replace(args['curve_evidence'], curve_sha256=digest)
            args['availability_evidence'] = replace(args['availability_evidence'], curve_sha256=digest)
            with self.subTest(summary=summary), self.assertRaises(c.CurveUnavailable): c.export_cusum_curve(**args)

    def test_availability_evidence_required_and_native_cannot_use_replay_basis(self):
        args = fixture(); args['availability_evidence'] = None
        with self.assertRaises(ValueError): c.export_cusum_curve(**args)
        args = fixture(); args['availability_evidence'] = replace(args['availability_evidence'],
            query_availability=args['availability_evidence'].query_availability[:-1])
        with self.assertRaises(ValueError): c.export_cusum_curve(**args)
        args = fixture('lower', .5, chronology='native')
        self.assertEqual(c.export_cusum_curve(**args)['availability_basis'], 'observed_query_position')
        args['availability_evidence'] = replace(args['availability_evidence'], basis='declared_fixed_replay')
        with self.assertRaises(ValueError): c.export_cusum_curve(**args)

    def test_unverified_availability_record_or_binding_rejected(self):
        for field, value in (('curve_sha256', sha(99)), ('manifest_sha256', sha(99)),
                             ('basis', 'inferred'), ('record_sha256', sha(99))):
            args = fixture(); args['availability_evidence'] = replace(args['availability_evidence'], **{field: value})
            with self.subTest(field=field), self.assertRaises(ValueError): c.export_cusum_curve(**args)
        args = fixture(); args['evidence_records'][args['availability_evidence'].record_sha256] = b'999'
        with self.assertRaises(ValueError): c.export_cusum_curve(**args)

    def test_score_membership_missing_fields_and_warmup_are_not_filled(self):
        for mutate in (lambda rows: rows[0].update(query_slice_sha256=sha(99)),
                       lambda rows: rows[0].pop('available_at'),
                       lambda rows: rows[0].pop('computed_through'),
                       lambda rows: rows[0].update(start=101, end=101)):
            args = fixture(); changed_rows(args, mutate, update_availability=False)
            with self.assertRaises(ValueError): c.export_cusum_curve(**args)

    def test_no_mutation_of_existing_sources_or_results(self):
        root = Path(__file__).resolve().parents[2]
        paths = ['stream_prada_order/phase_d_pilot.py', 'stream_prada_order/experiment.py',
                 'stream_prada_order/hybrid_fusion.py', 'stream_prada_order/hybrid_integration.py',
                 'stream_prada_order/common_stream_producer.py',
                 'stream_prada_order/results/phase_d_pilot_20261107_v2/per_stream.csv.gz']
        def hashes(): return {p: hashlib.sha256((root / p).read_bytes()).hexdigest() for p in paths}
        before = hashes(); c.export_cusum_curve(**fixture())
        self.assertEqual(hashes(), before)

    def test_strict_json_and_explicit_profile_no_new_schema(self):
        args = fixture(); args['profile'] = None
        with self.assertRaises(ValueError): c.export_cusum_curve(**args)
        args = fixture(); args['raw_curve'] = b'[{"value":0,"value":1}]'
        digest = hashlib.sha256(args['raw_curve']).hexdigest()
        args['curve_evidence'] = replace(args['curve_evidence'], curve_sha256=digest)
        args['availability_evidence'] = replace(args['availability_evidence'], curve_sha256=digest)
        with self.assertRaises(ValueError): c.export_cusum_curve(**args)


if __name__ == '__main__': unittest.main()
