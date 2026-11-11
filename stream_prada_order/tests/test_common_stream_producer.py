"""Synthetic numeric metadata only: no research texts, vectors or real receipts."""
import copy
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from stream_prada_order import common_stream_producer as p
from stream_prada_order import hybrid_fusion as h
from stream_prada_order import hybrid_integration as a
from stream_prada_order.tests.test_hybrid_integration import fixture, PROFILE, sha


def inputs(kind='fixed_query_replay'):
    manifest, cert, index, _ = fixture()
    manifest['chronology_kind'] = kind
    requests = manifest.pop('queries')
    physical = p.PhysicalEmbeddingEvidence(
        receipt_sha256=sha(6001), verifier_revision=sha(6002),
        embedding_artifact_sha256=manifest['representation']['embedding_artifact_sha256'],
        embedding_index_sha256=h.fingerprint(index),
        representation_sha256=h.fingerprint(manifest['representation']),
        row_count=256, layout='contiguous-little-endian')
    evidence = p.SourceEvidence(
        authorized=True, authorization_record_sha256=sha(6003),
        authorized_manifest_sha256=h.fingerprint({**manifest, 'queries': requests}),
        grouping_certificate_sha256=h.fingerprint(cert),
        chronology_kind=kind,
        chronology_basis='observed_request_order' if kind == 'native' else 'declared_fixed_replay',
        chronology_record_sha256=sha(6004), ordered_query_sha256=h.fingerprint(requests),
        physical_embeddings=physical)
    return dict(metadata=manifest, ordered_requests=requests, certificate=cert,
                embedding_index=index, expected_representation=copy.deepcopy(manifest['representation']),
                evidence=evidence, profile=PROFILE,
                evidence_records={sha(6001): b'6001', sha(6003): b'6003', sha(6004): b'6004',
                                  cert['provenance_sha256']: b'1'})


def rebind_order(args):
    """Only for tests of internally consistent synthetic metadata changes."""
    args['evidence'] = replace(args['evidence'],
        authorized_manifest_sha256=h.fingerprint({**args['metadata'], 'queries': args['ordered_requests']}),
        ordered_query_sha256=h.fingerprint(args['ordered_requests']))


class ProducerTests(unittest.TestCase):
    def test_valid_ordered_manifest_uses_existing_contract_without_mutation(self):
        args = inputs(); before = copy.deepcopy(args)
        result = p.produce_manifest(**args)
        self.assertEqual(result, {**args['metadata'], 'queries': args['ordered_requests']})
        self.assertEqual(a.validate_manifest(result, args['certificate'], args['embedding_index'], PROFILE).session_id, '1')
        self.assertEqual(args, before)
        result['queries'][0]['request_id'] = 'changed'
        self.assertEqual(args, before)

    def test_missing_request_identity(self):
        args = inputs(); del args['ordered_requests'][0]['request_id']
        with self.assertRaises(ValueError): p.produce_manifest(**args)

    def test_duplicate_request_id(self):
        args = inputs(); args['ordered_requests'][1]['request_id'] = '1'
        with self.assertRaisesRegex(ValueError, 'duplicate_request_id'): p.produce_manifest(**args)

    def test_repeated_text_and_embedding_keep_distinct_requests(self):
        args = inputs()
        for key in ('text_sha256', 'embedding_row', 'embedding_row_sha256'):
            args['ordered_requests'][1][key] = args['ordered_requests'][0][key]
        rebind_order(args)
        result = p.produce_manifest(**args)
        self.assertEqual(len(result['queries']), 256)
        self.assertEqual([q['request_id'] for q in result['queries'][:2]], ['1', '2'])
        self.assertEqual(result['queries'][0]['text_sha256'], result['queries'][1]['text_sha256'])

    def test_wrong_embedding_row_hash(self):
        args = inputs(); args['ordered_requests'][0]['embedding_row_sha256'] = sha(999)
        with self.assertRaisesRegex(ValueError, 'query_embedding_row_mismatch'): p.produce_manifest(**args)

    def test_missing_provenance_fails_closed(self):
        for field in ('authorization_record_sha256', 'chronology_record_sha256', 'grouping_certificate_sha256'):
            with self.subTest(field=field):
                args = inputs(); args['evidence'] = replace(args['evidence'], **{field: None})
                with self.assertRaises(ValueError): p.produce_manifest(**args)
        for evidence in (None, replace(inputs()['evidence'], authorized=False)):
            args = inputs(); args['evidence'] = evidence
            with self.assertRaises(ValueError): p.produce_manifest(**args)
        args = inputs(); del args['metadata']['dataset_revision']
        with self.assertRaises(ValueError): p.produce_manifest(**args)

    def test_out_of_order_indices_never_sorted_or_renumbered(self):
        args = inputs(); args['ordered_requests'][0], args['ordered_requests'][1] = args['ordered_requests'][1], args['ordered_requests'][0]
        with self.assertRaisesRegex(ValueError, 'query_positions_not_contiguous'): p.produce_manifest(**args)

    def test_representation_mismatch_including_consistently_relabelled_encoder(self):
        for field, value in (('encoder_revision', sha(990)), ('tokenizer_revision', sha(991)),
                             ('preprocessing_sha256', sha(992)), ('normalized', False),
                             ('dtype', 'float64'), ('dimension', 3)):
            with self.subTest(field=field):
                args = inputs(); args['metadata']['representation'][field] = value
                args['embedding_index']['representation_sha256'] = h.fingerprint(args['metadata']['representation'])
                rebind_order(args)
                with self.assertRaisesRegex(ValueError, 'expected_representation_mismatch'): p.produce_manifest(**args)

    def test_native_and_replay_require_explicit_matching_evidence(self):
        for kind in ('native', 'fixed_query_replay'):
            args = inputs(kind)
            self.assertEqual(p.produce_manifest(**args)['chronology_kind'], kind)
            args['evidence'] = replace(args['evidence'], chronology_basis='dataset_row_order')
            with self.assertRaises(ValueError): p.produce_manifest(**args)
        args = inputs(); args['metadata']['chronology_kind'] = 'native'; rebind_order(args)
        with self.assertRaisesRegex(ValueError, 'chronology_evidence_mismatch'): p.produce_manifest(**args)

    def test_deterministic_canonical_fingerprint_and_written_bytes(self):
        args = inputs(); first = p.produce_manifest(**args)
        args['metadata'] = dict(reversed(list(args['metadata'].items())))
        self.assertEqual(p.produce_manifest(**args), first)
        with tempfile.TemporaryDirectory() as directory:
            dest = Path(directory) / 'manifest.json'
            fingerprint = p.write_manifest(dest, **args)
            self.assertEqual(json.loads(dest.read_bytes()), first)
            self.assertEqual(fingerprint, h.fingerprint(first))
            self.assertEqual(hashlib.sha256(dest.read_bytes()).hexdigest(), fingerprint)

    def test_invalid_lengths_and_incomplete_manifest(self):
        for count in (0, 100, 255, 257):
            args = inputs(); args['ordered_requests'] = (args['ordered_requests'] + args['ordered_requests'])[:count]
            with self.subTest(count=count), self.assertRaises(ValueError): p.produce_manifest(**args)
        args = inputs(); args['profile'] = None
        with self.assertRaises(ValueError): p.produce_manifest(**args)

    def test_no_output_or_directory_created_on_any_validation_failure(self):
        for change in ('request', 'authorization', 'physical', 'ordering'):
            args = inputs()
            if change == 'request': args['ordered_requests'][0]['request_id'] = ''
            elif change == 'authorization': args['evidence'] = replace(args['evidence'], authorized=False)
            elif change == 'physical': args['evidence'] = replace(args['evidence'], physical_embeddings=None)
            else: args['ordered_requests'].reverse()
            with self.subTest(change=change), tempfile.TemporaryDirectory() as directory:
                parent = Path(directory) / 'not-created'; dest = parent / 'manifest.json'
                with self.assertRaises(ValueError): p.write_manifest(dest, **args)
                self.assertFalse(parent.exists())

    def test_existing_file_never_overwritten_even_when_invalid(self):
        with tempfile.TemporaryDirectory() as directory:
            dest = Path(directory) / 'manifest.json'; dest.write_bytes(b'123')
            with self.assertRaises(FileExistsError): p.write_manifest(dest, **inputs())
            args = inputs(); args['evidence'] = None
            with self.assertRaises(ValueError): p.write_manifest(dest, **args)
            self.assertEqual(dest.read_bytes(), b'123')

    def test_physical_evidence_binding_and_row_layout_required(self):
        for field, value in (('receipt_sha256', None), ('verifier_revision', ''),
                             ('embedding_artifact_sha256', sha(10)), ('embedding_index_sha256', sha(11)),
                             ('representation_sha256', sha(12)), ('row_count', 255),
                             ('row_count', True), ('layout', 'unspecified')):
            args = inputs(); physical = replace(args['evidence'].physical_embeddings, **{field: value})
            args['evidence'] = replace(args['evidence'], physical_embeddings=physical)
            with self.subTest(field=field, value=value), self.assertRaises(ValueError): p.produce_manifest(**args)

    def test_changed_order_with_renumbering_cannot_reuse_audit(self):
        args = inputs(); args['ordered_requests'].reverse()
        for position, request in enumerate(args['ordered_requests'], 1): request['query_index'] = position
        with self.assertRaisesRegex(ValueError, 'ordered_query_evidence_mismatch'): p.produce_manifest(**args)

    def test_split_group_and_certificate_mismatches(self):
        args = inputs(); args['metadata']['split'] = 'final_test'
        with self.assertRaises(ValueError): p.produce_manifest(**args)
        args = inputs(); args['ordered_requests'][0]['source_group_sha256'] = sha(42)
        with self.assertRaises(ValueError): p.produce_manifest(**args)
        args = inputs(); args['certificate']['provenance_sha256'] = sha(43)
        with self.assertRaises(ValueError): p.produce_manifest(**args)

    def test_authorization_and_physical_receipt_cannot_be_reused_for_other_manifest(self):
        args = inputs(); args['metadata']['session_id'] = 'different'
        with self.assertRaisesRegex(ValueError, 'authorization_manifest_mismatch'): p.produce_manifest(**args)
        args = inputs(); args['embedding_index']['rows'][0]['text_sha256'] = sha(5)
        with self.assertRaises(ValueError): p.produce_manifest(**args)

    def test_missing_tampered_or_empty_evidence_records_cannot_write_output(self):
        for field in ('authorization_record_sha256', 'chronology_record_sha256'):
            args = inputs(); del args['evidence_records'][getattr(args['evidence'], field)]
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, 'evidence_record_required'):
                p.produce_manifest(**args)
        for value in (None, b'', b'9999', '6001', b'1' * (1024**2 + 1)):
            args = inputs(); key = args['evidence'].physical_embeddings.receipt_sha256
            args['evidence_records'][key] = value
            with self.subTest(value_type=type(value).__name__), tempfile.TemporaryDirectory() as directory:
                dest = Path(directory) / 'manifest.json'
                with self.assertRaises(ValueError): p.write_manifest(dest, **args)
                self.assertFalse(dest.exists())
        args = inputs(); del args['evidence_records'][args['certificate']['provenance_sha256']]
        with self.assertRaisesRegex(ValueError, 'evidence_record_required'): p.produce_manifest(**args)


if __name__ == '__main__': unittest.main()
