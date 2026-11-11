"""Synthetic numeric accounting fixtures; no research calibration/artifacts."""
import copy
from dataclasses import FrozenInstanceError, replace
from types import MappingProxyType
import unittest

from stream_prada_order import hybrid_fusion as h
from stream_prada_order import hybrid_integration as a
from stream_prada_order.tests.test_hybrid_fusion import CONTEXT, SEQ, MMD

PROFILE = 'research_256_grid_proposal_v1'


def fixture(values=None, *, label='attack', unavailable=None, schedule=None):
    schedule = schedule or a.schedule(PROFILE)
    spec = h.Spec(CONTEXT, SEQ, MMD, schedule)
    # Fixed synthetic calibrated metadata, not fit/calibrate calls or research
    # observations. Raw0 maps to.5, raw3 to1; the fixed threshold is.75.
    normalizer = h.Normalizer(spec, (0., 1., 2.), (0., 1., 2.),
        (('1', h.fingerprint(1), '1'),), h.fingerprint(11))
    model = h.Calibrated(normalizer, (('2', h.fingerprint(2), '2'),),
        MappingProxyType({method: h.Threshold(.75, 19, 19, .05) for method in h.METHODS}), h.fingerprint(12))
    stream = h.Stream('8', h.fingerprint(8), '8', 'validation', label, CONTEXT)
    values = tuple(0. for _ in schedule.checkpoints) if values is None else values
    assert len(values) == len(schedule.checkpoints)
    tables = []
    for component, revision in (('sequential', SEQ), ('mmd', MMD)):
        records = []
        for end, value in zip(schedule.checkpoints, values):
            state = (unavailable or {}).get((component, end))
            if state == 'missing': continue
            start = end if component == 'sequential' else end - schedule.window + 1
            records.append(h.Score(stream, revision, start, end, end + 1 if state == 'late' else end,
                                   None if state == 'invalid' else value, state != 'invalid', end))
        tables.append(records)
    return model, h.align(spec, stream, *tables)


def report(model, rows, method='weighted', *, onset=1, profile=PROFILE):
    # Deferred import permits the mandatory legacy-behavior confirmation before
    # any adapter implementation exists.
    from stream_prada_order import hybrid_endpoint_adapter as e
    return e.evaluate_by_q250(model, rows, method, profile=profile, attack_onset=onset)


class LegacyBehaviorTests(unittest.TestCase):
    def test_existing_256_no_alert_censors_at256_despite_last_look250(self):
        model, rows = fixture()
        result = h.evaluate(model, rows, 'weighted', attack_onset=1)
        self.assertEqual(result.checkpoints, (150, 200, 250))
        self.assertTrue(result.complete)
        self.assertEqual(result.decisions, (False, False, False))
        self.assertEqual(result.censor_query, 256)

    def test_existing_300_censor_and_terminal_alert_remain_unchanged(self):
        schedule = a.schedule('illustrative_300_v1')
        model, rows = fixture(schedule=schedule)
        self.assertEqual(h.evaluate(model, rows, 'weighted', attack_onset=1).censor_query, 300)
        model, rows = fixture((0., 0., 0., 3.), schedule=schedule)
        alert = h.evaluate(model, rows, 'weighted', attack_onset=1)
        self.assertEqual(alert.first_alert_query, 300)
        self.assertEqual(alert.detection_delay, 299)


class EndpointAdapterTests(unittest.TestCase):
    def test_complete_no_alert_reports_distinct_horizon_endpoint_and_censor250(self):
        model, rows = fixture(); result = report(model, rows)
        self.assertEqual((result.recorded_horizon, result.evaluation_end), (256, 250))
        self.assertEqual(result.profile_id, PROFILE)
        self.assertEqual(result.checkpoints, (150, 200, 250))
        self.assertIs(result.any_alert_by_q250, False)
        self.assertEqual(result.censor_query, 250)
        self.assertIsNone(result.detection_delay)
        self.assertTrue(result.scheduled_post_onset_opportunity)
        self.assertEqual(result.post_onset_status, 'censored')
        self.assertEqual(h.evaluate(model, rows, 'weighted', attack_onset=1).censor_query, 256)

    def test_exact_alerts_and_delay_at_each_joint_checkpoint(self):
        for index, end in enumerate((150, 200, 250)):
            values = tuple(3. if i == index else 0. for i in range(3))
            model, rows = fixture(values); result = report(model, rows, onset=110)
            with self.subTest(end=end):
                self.assertTrue(result.any_alert_by_q250)
                self.assertEqual(result.first_observed_alert, end)
                self.assertEqual(result.first_alert_query, end)
                self.assertTrue(result.first_alert_exact)
                self.assertEqual(result.detection_delay, end - 110)
                self.assertIsNone(result.censor_query)
                self.assertEqual(result.post_onset_status, 'detected')

    def test_pre_attack_alarm_is_retained_without_attack_delay_or_censor(self):
        model, rows = fixture((3., 0., 0.)); result = report(model, rows, onset=180)
        self.assertTrue(result.pre_attack_alarm)
        self.assertTrue(result.any_alert_by_q250)
        self.assertEqual(result.first_alert_query, 150)
        self.assertEqual(result.post_onset_status, 'pre_attack_alarm')
        self.assertIsNone(result.detection_delay); self.assertIsNone(result.censor_query)

    def test_onset1_has_no_benign_prefix_and_full_delay(self):
        model, rows = fixture((3., 0., 0.)); result = report(model, rows, onset=1)
        self.assertIsNone(result.pre_attack_alarm)
        self.assertEqual(result.detection_delay, 149)

    def test_onset250_has_one_scheduled_opportunity(self):
        model, rows = fixture((0., 0., 3.)); result = report(model, rows, onset=250)
        self.assertTrue(result.scheduled_post_onset_opportunity)
        self.assertFalse(result.pre_attack_alarm)
        self.assertEqual(result.detection_delay, 0)
        model, rows = fixture(); result = report(model, rows, onset=250)
        self.assertEqual(result.censor_query, 250)

    def test_onset251_and256_never_become_evaluated_attack_misses(self):
        for onset in (251, 256):
            for values in ((0., 0., 0.), (3., 0., 0.)):
                model, rows = fixture(values); result = report(model, rows, onset=onset)
                with self.subTest(onset=onset, values=values):
                    self.assertFalse(result.scheduled_post_onset_opportunity)
                    self.assertEqual(result.post_onset_status, 'no_scheduled_post_onset_opportunity')
                    self.assertIsNone(result.censor_query); self.assertIsNone(result.detection_delay)
                    self.assertEqual(result.any_alert_by_q250, values[0] == 3.)
                    self.assertEqual(result.pre_attack_alarm, values[0] == 3.)

    def test_missing_invalid_late_and_stale_preserve_unknown_no_alert(self):
        for end, state, reason in ((150, 'missing', 'missing'), (200, 'missing', 'stale'),
                                   (200, 'invalid', 'invalid'), (250, 'late', 'not_available')):
            model, rows = fixture(unavailable={('mmd', end): state}); result = report(model, rows)
            with self.subTest(state=state, end=end):
                self.assertFalse(result.complete); self.assertFalse(result.joint_complete)
                self.assertIsNone(result.any_alert_by_q250)
                self.assertIsNone(result.censor_query); self.assertIsNone(result.detection_delay)
                self.assertEqual(result.post_onset_status, 'incomplete')
                self.assertEqual(result.points[result.checkpoints.index(end)].mmd_reason, reason)

    def test_observed_event_after_unavailable_look_has_unknown_exact_first_alert(self):
        for state in ('missing', 'invalid', 'late'):
            model, rows = fixture((0., 3., 0.), unavailable={('mmd', 150): state})
            result = report(model, rows)
            with self.subTest(state=state):
                self.assertEqual(result.decisions, (None, True, False))
                self.assertTrue(result.any_alert_by_q250)
                self.assertEqual(result.first_observed_alert, 200)
                self.assertIsNone(result.first_alert_query); self.assertFalse(result.first_alert_exact)
                self.assertIsNone(result.pre_attack_alarm)
                self.assertIsNone(result.detection_delay); self.assertIsNone(result.censor_query)

    def test_later_missing_look_preserves_known_first_alert_but_no_complete_delay(self):
        model, rows = fixture((3., 0., 0.), unavailable={('mmd', 250): 'late'})
        result = report(model, rows)
        self.assertTrue(result.any_alert_by_q250); self.assertTrue(result.first_alert_exact)
        self.assertEqual(result.first_alert_query, 150); self.assertFalse(result.complete)
        self.assertIsNone(result.detection_delay); self.assertIsNone(result.censor_query)

    def test_late_onset_with_incomplete_records_still_has_no_opportunity(self):
        model, rows = fixture(unavailable={('mmd', 150): 'invalid'})
        result = report(model, rows, onset=251)
        self.assertFalse(result.scheduled_post_onset_opportunity)
        self.assertEqual(result.post_onset_status, 'no_scheduled_post_onset_opportunity')
        self.assertIsNone(result.any_alert_by_q250); self.assertIsNone(result.censor_query)

    def test_benign_and_unknown_onset_never_receive_post_onset_censor(self):
        model, rows = fixture(label='benign'); result = report(model, rows, onset=None)
        self.assertIs(result.any_alert_by_q250, False)
        self.assertIsNone(result.scheduled_post_onset_opportunity)
        self.assertEqual(result.post_onset_status, 'not_applicable_benign')
        self.assertIsNone(result.censor_query)
        model, rows = fixture(); result = report(model, rows, onset=None)
        self.assertEqual(result.post_onset_status, 'onset_unknown')
        self.assertIsNone(result.scheduled_post_onset_opportunity); self.assertIsNone(result.censor_query)

    def test_component_only_completeness_is_distinct_from_joint_coverage(self):
        model, rows = fixture(unavailable={('mmd', 150): 'missing'})
        result = report(model, rows, method='sequential_only')
        self.assertTrue(result.complete); self.assertFalse(result.joint_complete)
        self.assertIs(result.any_alert_by_q250, False); self.assertEqual(result.censor_query, 250)
        self.assertIsNone(report(model, rows, method='weighted').any_alert_by_q250)

    def test_wrong_profile_and_every_schedule_field_are_rejected(self):
        model, rows = fixture()
        for profile in (None, 'illustrative_300_v1', 'unknown'):
            with self.subTest(profile=profile), self.assertRaises(ValueError): report(model, rows, profile=profile)
        for changes in ({'horizon': 255}, {'horizon': 300}, {'window': 99}, {'stride': 51}, {'first_eligible': 101}):
            model, rows = fixture(schedule=replace(a.schedule(PROFILE), **changes))
            with self.subTest(changes=changes), self.assertRaises(ValueError): report(model, rows)

    def test_compatible_model_alignment_method_and_onset_checks_are_reused(self):
        model, rows = fixture()
        with self.assertRaises(ValueError): report(model, replace(rows, spec=replace(rows.spec, sequential_weight=.7)))
        with self.assertRaises(ValueError): report(model, replace(rows, points=rows.points[:-1]))
        with self.assertRaises(ValueError): report(model, rows, method='unknown')
        for onset in (0, 257, True):
            with self.assertRaises(ValueError): report(model, rows, onset=onset)
        model, rows = fixture(label='benign')
        with self.assertRaises(ValueError): report(model, rows, onset=1)

    def test_no_inputs_raw_points_threshold_or_provenance_mutation(self):
        model, rows = fixture((0., 3., 0.)); receipt = copy.deepcopy(model.receipt()); before = copy.deepcopy(rows)
        legacy = h.evaluate(model, rows, 'weighted', attack_onset=1)
        result = report(model, rows)
        self.assertEqual(model.receipt(), receipt); self.assertEqual(rows, before)
        self.assertEqual(result.points, rows.points); self.assertEqual(result.spec, rows.spec)
        self.assertEqual(result.threshold, model.thresholds['weighted'])
        self.assertEqual(result.calibration_provenance, model.provenance_sha256)
        for field in ('stream', 'method', 'decisions', 'checkpoints', 'complete', 'first_observed_alert',
                      'first_alert_query', 'first_alert_exact', 'attack_onset', 'pre_attack_alarm', 'detection_delay'):
            self.assertEqual(getattr(result, field), getattr(legacy, field))

    def test_reporting_record_is_separate_and_immutable(self):
        model, rows = fixture(); result = report(model, rows)
        self.assertNotIsInstance(result, h.Result)
        with self.assertRaises(FrozenInstanceError): result.censor_query = 256
        with self.assertRaises(FrozenInstanceError): result.points[0].mmd = 9.
        with self.assertRaises(FrozenInstanceError): result.threshold.value = .2

    def test_reporting_points_do_not_alias_a_mutable_input_container(self):
        model, rows = fixture(); mutable = replace(rows, points=list(rows.points))
        result = report(model, mutable)
        self.assertIsInstance(result.points, tuple)
        mutable.points.pop()
        self.assertEqual(len(result.points), 3)

    def test_mutable_threshold_metadata_is_not_a_compatible_calibrated_record(self):
        model, rows = fixture()
        thresholds = dict(model.thresholds)
        thresholds['weighted'] = replace(thresholds['weighted'], rank=[19])
        with self.assertRaises(ValueError): report(replace(model, thresholds=thresholds), rows)
        with self.assertRaises(ValueError): report(replace(model, provenance_sha256=[12]), rows)


if __name__ == '__main__': unittest.main()
