"""Synthetic numeric metadata only; no scoring, calibration or research data."""
import copy
from dataclasses import asdict, fields, FrozenInstanceError, replace
import hashlib
import unittest
from unittest import mock

from stream_prada_order import paired_stream_admission as p
from stream_prada_order import cusum_curve_exporter as c
from stream_prada_order import deep_kernel_mmd_exporter as m
from stream_prada_order import hybrid_fusion as h
from stream_prada_order import hybrid_integration as a
from stream_prada_order.tests.test_deep_kernel_mmd_exporter import fixture as producer_fixture, changed_rows as mmd_changed
from stream_prada_order.tests.test_cusum_curve_exporter import changed_rows as cusum_changed
from stream_prada_order.tests.test_hybrid_integration import PROFILE, sha


def fixture():
    md, sd = producer_fixture()
    args = dict(cusum=p.CUSUMInputs(**{f.name: sd[f.name] for f in fields(p.CUSUMInputs)}),
        deep_kernel=p.DeepKernelInputs(**{f.name: md[f.name] for f in fields(p.DeepKernelInputs)}),
        profile=PROFILE, expected_representation=copy.deepcopy(sd['expected_representation']),
        expected_cusum_revision=sd['expected_revision'], expected_cusum_definition=sd['expected_definition'],
        expected_mmd_revision=md['expected_revision'], expected_mmd_definition=md['expected_definition'])
    return args, sd, md


def updated_inputs(args, sd=None, md=None):
    if sd is not None:
        args['cusum'] = p.CUSUMInputs(**{f.name: sd[f.name] for f in fields(p.CUSUMInputs)})
    if md is not None:
        args['deep_kernel'] = p.DeepKernelInputs(**{f.name: md[f.name] for f in fields(p.DeepKernelInputs)})


class PairedAdmissionTests(unittest.TestCase):
    def test_valid_pair_calls_both_real_exporters_then_existing_alignment(self):
        args, _, _ = fixture()
        with mock.patch.object(c, 'export_cusum_curve', wraps=c.export_cusum_curve) as cs, \
             mock.patch.object(m, 'export_deep_kernel_mmd', wraps=m.export_deep_kernel_mmd) as dk, \
             mock.patch.object(a, 'align_exports', wraps=a.align_exports) as align, \
             mock.patch.object(h, 'evaluate', side_effect=AssertionError('no evaluation')), \
             mock.patch.object(h, 'calibrate', side_effect=AssertionError('no calibration')):
            result = p.admit_and_align(**args)
        self.assertTrue(result.contract_admitted); self.assertIsNone(result.diagnostic)
        self.assertIsNotNone(result.pair); cs.assert_called_once(); dk.assert_called_once(); align.assert_called_once()
        pair = result.pair
        self.assertEqual([pt.query_index for pt in pair.aligned.points], [150, 200, 250])
        self.assertEqual([pt.mmd for pt in pair.aligned.points], [-.1, -.1, -.1])
        self.assertEqual([(s.start, s.end) for s in pair.mmd_scores if s.end >= 150],
                         [(51, 150), (101, 200), (151, 250)])
        self.assertEqual([look.joint_available for look in pair.joint_availability], [True, True, True])
        self.assertTrue(pair.joint_complete)
        self.assertEqual(pair.cusum_revision, args['expected_cusum_revision'])
        self.assertEqual(pair.mmd_revision, args['expected_mmd_revision'])
        self.assertNotEqual(pair.cusum_revision, pair.mmd_revision)

    def test_input_identities_are_exact_deterministic_and_use_actual_bytes(self):
        args, sd, md = fixture(); first = p.admit_and_align(**args).pair.identities
        self.assertEqual(first.common_manifest_sha256, h.fingerprint(sd['manifest']))
        self.assertEqual(first.ordered_query_sha256, h.fingerprint(sd['manifest']['queries']))
        self.assertEqual(first.embedding_index_sha256, h.fingerprint(sd['embedding_index']))
        self.assertEqual(first.grouping_certificate_sha256, h.fingerprint(sd['certificate']))
        self.assertEqual(first.reference_manifest_sha256, h.fingerprint(md['reference']))
        self.assertEqual(first.cusum_curve_sha256, hashlib.sha256(sd['raw_curve']).hexdigest())
        self.assertEqual(first.mmd_score_sha256, hashlib.sha256(md['raw_scores']).hexdigest())
        args['expected_representation'] = dict(reversed(list(args['expected_representation'].items())))
        self.assertEqual(p.admit_and_align(**args).pair.identities, first)
        sd['evidence_records'][sha(999)] = b'999'
        updated_inputs(args, sd=sd, md=md)
        second = p.admit_and_align(**args).pair.identities
        self.assertNotEqual(first.cusum_input_sha256, second.cusum_input_sha256)
        self.assertNotEqual(first.mmd_input_sha256, second.mmd_input_sha256)
        self.assertEqual(first.expectations_sha256, second.expectations_sha256)

    def test_different_manifests_orders_indices_or_certificates_are_not_pairs(self):
        for field, mutate, expected_code in (
            ('manifest', lambda x: x.update(session_id='9'), 'common_manifest_mismatch'),
            ('manifest', lambda x: x['queries'].reverse(), 'common_manifest_mismatch'),
            ('embedding_index', lambda x: x['rows'][0].update(embedding_row_sha256=sha(99)), 'embedding_index_mismatch'),
            ('certificate', lambda x: x.update(provenance_sha256=sha(99)), 'group_certificate_mismatch')):
            args, _, _ = fixture(); value = copy.deepcopy(getattr(args['deep_kernel'], field)); mutate(value)
            args['deep_kernel'] = replace(args['deep_kernel'], **{field: value})
            with self.subTest(field=field), mock.patch.object(c, 'export_cusum_curve', wraps=c.export_cusum_curve) as cs:
                result = p.admit_and_align(**args)
                self.assertFalse(result.contract_admitted); self.assertIsNone(result.pair)
                self.assertEqual(result.diagnostic.stage, 'shared_identity')
                self.assertEqual(result.diagnostic.code, expected_code); cs.assert_not_called()

    def test_identically_wrong_shared_certificate_still_fails_export_validation(self):
        args, _, _ = fixture(); bad = copy.deepcopy(args['cusum'].certificate); bad['provenance_sha256'] = sha(99)
        args['cusum'] = replace(args['cusum'], certificate=bad)
        args['deep_kernel'] = replace(args['deep_kernel'], certificate=copy.deepcopy(bad))
        result = p.admit_and_align(**args)
        self.assertFalse(result.contract_admitted); self.assertIsNone(result.pair)
        self.assertEqual(result.diagnostic.stage, 'cusum_export')

    def test_independent_expected_revisions_never_replaced_by_producer_claims(self):
        for key in ('expected_cusum_revision', 'expected_mmd_revision'):
            for field in ('detector_revision', 'model_revision', 'configuration_revision', 'calibration_provenance'):
                args, _, _ = fixture(); args[key] = replace(args[key], **{field: sha(99)})
                with self.subTest(key=key, field=field):
                    result = p.admit_and_align(**args)
                    self.assertFalse(result.contract_admitted); self.assertIsNone(result.pair)
                    self.assertEqual(result.diagnostic.stage, 'cusum_export' if 'cusum' in key else 'mmd_export')

    def test_independent_expected_representation_and_definitions_not_inferred(self):
        args, _, _ = fixture(); args['expected_representation']['encoder_revision'] = sha(99)
        self.assertFalse(p.admit_and_align(**args).contract_admitted)
        for key, change in (('expected_cusum_definition', {'k': 1.}), ('expected_mmd_definition', {'epsilon': .2})):
            args, _, _ = fixture(); args[key] = replace(args[key], **change)
            with self.subTest(key=key): self.assertFalse(p.admit_and_align(**args).contract_admitted)

    def test_missing_cusum_curve_gives_no_partial_pair_and_never_calls_mmd(self):
        args, _, _ = fixture(); args['cusum'] = replace(args['cusum'], raw_curve=None)
        with mock.patch.object(m, 'export_deep_kernel_mmd', wraps=m.export_deep_kernel_mmd) as md, \
             mock.patch.object(a, 'align_exports', wraps=a.align_exports) as align:
            result = p.admit_and_align(**args)
        self.assertFalse(result.contract_admitted); self.assertIsNone(result.pair)
        self.assertEqual((result.diagnostic.stage, result.diagnostic.code), ('cusum_export', 'cusum_curve_unavailable'))
        md.assert_not_called(); align.assert_not_called()

    def test_missing_required_mmd_window_gives_no_pair_after_successful_cusum(self):
        args, _, md = fixture(); mmd_changed(md, lambda rows: rows.pop(2)); updated_inputs(args, md=md)
        with mock.patch.object(c, 'export_cusum_curve', wraps=c.export_cusum_curve) as cs, \
             mock.patch.object(a, 'align_exports', wraps=a.align_exports) as align:
            result = p.admit_and_align(**args)
        self.assertFalse(result.contract_admitted); self.assertIsNone(result.pair)
        self.assertEqual((result.diagnostic.stage, result.diagnostic.code), ('mmd_export', 'mmd_windows_unavailable'))
        cs.assert_called_once(); align.assert_not_called()

    def test_missing_or_tampered_provenance_is_rejected_at_responsible_exporter(self):
        for role in ('cusum', 'mmd'):
            args, sd, md = fixture()
            key = sd['curve_evidence'].provenance_record_sha256 if role == 'cusum' else md['score_evidence'].provenance_record_sha256
            for value in (None, b'999'):
                changed = copy.deepcopy(args)
                records = changed['cusum'].evidence_records if role == 'cusum' else changed['deep_kernel'].evidence_records
                if value is None: records.pop(key)
                else: records[key] = value
                result = p.admit_and_align(**changed)
                self.assertFalse(result.contract_admitted); self.assertIsNone(result.pair)
                self.assertEqual(result.diagnostic.stage, 'cusum_export' if role == 'cusum' else 'mmd_export')

    def test_invalid_and_late_scores_admitted_with_incomplete_joint_coverage(self):
        for role in ('cusum', 'mmd'):
            for state in ('invalid', 'late'):
                args, sd, md = fixture()
                change = {'value': None, 'valid': False} if state == 'invalid' else {'available_at': 201}
                if role == 'cusum': cusum_changed(sd, lambda rows: rows[200-102].update(change))
                else: mmd_changed(md, lambda rows: rows[2].update(change))
                updated_inputs(args, sd=sd, md=md)
                result = p.admit_and_align(**args)
                with self.subTest(role=role, state=state):
                    self.assertTrue(result.contract_admitted); self.assertIsNone(result.diagnostic)
                    self.assertFalse(result.pair.joint_complete)
                    self.assertEqual([v.joint_available for v in result.pair.joint_availability], [True, False, True])
                    point = result.pair.aligned.points[1]
                    reason = point.sequential_reason if role == 'cusum' else point.mmd_reason
                    self.assertEqual(reason, 'invalid' if state == 'invalid' else 'not_available')
                    self.assertIsNone(point.sequential if role == 'cusum' else point.mmd)
                    records = result.pair.cusum_scores if role == 'cusum' else result.pair.mmd_scores
                    score = next(s for s in records if s.end == 200)
                    self.assertEqual(score.available_at, 200 if state == 'invalid' else 201)
                    self.assertEqual(score.value, None if state == 'invalid' else (float(200 % 9) if role == 'cusum' else -.1))

    def test_expected_contract_diagnostics_never_include_private_evidence_bytes(self):
        args, _, _ = fixture()
        def reject(*unused, **kwargs): h.require(False, b'PRIVATE_EVIDENCE_BYTES')
        with mock.patch.object(c, 'export_cusum_curve', side_effect=reject): result = p.admit_and_align(**args)
        self.assertFalse(result.contract_admitted); self.assertIsNone(result.pair)
        self.assertEqual(result.diagnostic.code, 'contract_rejected')
        self.assertNotIn('PRIVATE_EVIDENCE_BYTES', repr(asdict(result)))

    def test_malformed_source_json_is_a_sanitized_contract_rejection(self):
        args, sd, _ = fixture(); raw = b'PRIVATE_EVIDENCE_BYTES{'
        digest = hashlib.sha256(raw).hexdigest()
        args['cusum'] = replace(args['cusum'], raw_curve=raw,
            curve_evidence=replace(sd['curve_evidence'], curve_sha256=digest),
            availability_evidence=replace(sd['availability_evidence'], curve_sha256=digest))
        result = p.admit_and_align(**args)
        self.assertFalse(result.contract_admitted); self.assertIsNone(result.pair)
        self.assertEqual((result.diagnostic.stage, result.diagnostic.code), ('cusum_export', 'contract_rejected'))
        self.assertNotIn('PRIVATE_EVIDENCE_BYTES', repr(asdict(result)))

    def test_unexpected_programming_errors_propagate_not_disguised_as_rejection(self):
        for error in (RuntimeError('bug'), KeyError('bug'), TypeError('bug'), ValueError('bug')):
            args, _, _ = fixture()
            with mock.patch.object(c, 'export_cusum_curve', side_effect=error), self.assertRaises(type(error)):
                p.admit_and_align(**args)

    def test_no_unchecked_payload_bypass_and_profile_is_explicit(self):
        args, _, md = fixture(); args['cusum'] = {'kind': 'cusum_curve', 'rows': []}
        result = p.admit_and_align(**args)
        self.assertFalse(result.contract_admitted); self.assertIsNone(result.pair)
        for profile in (None, 'illustrative_300_v1', 'unknown'):
            args, _, _ = fixture(); args['profile'] = profile
            with self.subTest(profile=profile): self.assertFalse(p.admit_and_align(**args).contract_admitted)

    def test_alignment_rejection_does_not_return_exported_partial_success(self):
        args, _, _ = fixture()
        def reject(*unused, **kwargs): h.require(False, 'fixture_alignment_rejection')
        with mock.patch.object(a, 'align_exports', side_effect=reject): result = p.admit_and_align(**args)
        self.assertFalse(result.contract_admitted); self.assertIsNone(result.pair)
        self.assertEqual(result.diagnostic.stage, 'alignment')

    def test_inputs_preserved_and_success_reporting_containers_immutable(self):
        args, _, _ = fixture(); before = copy.deepcopy(args)
        result = p.admit_and_align(**args)
        self.assertEqual(args, before)
        self.assertIsInstance(result.pair.cusum_scores, tuple); self.assertIsInstance(result.pair.mmd_scores, tuple)
        self.assertIsInstance(result.pair.joint_availability, tuple)
        with self.assertRaises(FrozenInstanceError): result.contract_admitted = False
        with self.assertRaises(FrozenInstanceError): result.pair.joint_complete = False
        with self.assertRaises(FrozenInstanceError): result.pair.aligned.points[0].mmd = 1.
        with self.assertRaises(FrozenInstanceError): result.pair.identities.common_manifest_sha256 = sha(99)
        with self.assertRaises(FrozenInstanceError): result.pair.mmd_scores[0].available_at = 999
        args['cusum'].manifest['queries'].reverse()
        self.assertEqual([pt.query_index for pt in result.pair.aligned.points], [150, 200, 250])


if __name__ == '__main__': unittest.main()
