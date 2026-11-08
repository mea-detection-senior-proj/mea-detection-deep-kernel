"""Synthetic numeric scores only; no inference, detector calls or scientific data."""
import dataclasses as dc
import json
from pathlib import Path
import unittest
from stream_prada_order import hybrid_fusion as h

CONTEXT=h.Context('1','2','3','4')
SEQ=h.DetectorRevision('1','2','3','4')
MMD=h.DetectorRevision('5','6','7','8')
SPEC=h.Spec(CONTEXT,SEQ,MMD)

def stream(number=1,split='validation',label='benign',values=(0.,0.,0.,0.),group=None):
    key=h.Stream(str(number),str(number)*64 if number<10 else str(number).zfill(64),str(group or number),split,label,CONTEXT)
    sequential=tuple(h.Score(key,SEQ,t,t,t,v,True) for t,v in zip(SPEC.schedule.checkpoints,values))
    windows=tuple(h.Score(key,MMD,t-99,t,t,v,True) for t,v in zip(SPEC.schedule.checkpoints,values))
    return key,sequential,windows

def aligned(number=1,split='validation',values=(0.,0.,0.,0.),group=None,label='benign'):
    key,seq,mmd=stream(number,split,label=label,values=values,group=group)
    return h.align(SPEC,key,seq,mmd)

def model(alpha=.4):
    fit=h.fit_normalizer(SPEC,[aligned(1,'fit',(0.,1.,2.,3.))])
    return h.calibrate(fit,[aligned(2,'calibration',(0.,0.,0.,0.)),aligned(3,'calibration',(1.,1.,1.,1.))],alpha)

class AlignmentTests(unittest.TestCase):
    def test_predeclared_configuration_matches_defaults(self):
        config=json.loads((Path(__file__).resolve().parents[1]/'hybrid_fusion_config_v1.json').read_bytes())
        self.assertEqual(config['joint_checkpoints'],list(SPEC.schedule.checkpoints))
        self.assertEqual((config['horizon'],config['mmd_window'],config['mmd_stride'],config['sequential_first_eligible']),
                         (SPEC.schedule.horizon,SPEC.schedule.window,SPEC.schedule.stride,SPEC.schedule.first_eligible))
        self.assertEqual(config['weighted_fusion_sequential_weight'],SPEC.sequential_weight)
        self.assertEqual(config['methods'],list(h.METHODS))

    def test_checkpoints_and_inclusive_window_boundaries(self):
        self.assertEqual(SPEC.schedule.checkpoints,(150,200,250,300))
        rows=aligned();self.assertEqual([r.query_index for r in rows.points],[150,200,250,300])
        self.assertTrue(all(r.sequential_valid and r.mmd_valid for r in rows.points))

    def test_future_score_and_delayed_delivery_cannot_leak(self):
        key,seq,mmd=stream();a=h.align(SPEC,key,seq,mmd)
        future=dc.replace(mmd[-1],value=999999.)
        b=h.align(SPEC,key,seq,(*mmd[:-1],future))
        self.assertEqual(a.points[:3],b.points[:3])
        late=dc.replace(mmd[0],available_at=151)
        c=h.align(SPEC,key,seq,(late,*mmd[1:]))
        self.assertFalse(c.points[0].mmd_valid);self.assertEqual(c.points[0].mmd_reason,'not_available')

    def test_missing_stale_invalid_and_warmup(self):
        key,seq,mmd=stream();old=h.Score(key,MMD,1,100,100,99.,True)
        rows=h.align(SPEC,key,seq,(old,*mmd[1:]))
        self.assertEqual(rows.points[0].mmd_reason,'stale');self.assertIsNone(rows.points[0].mmd)
        invalid=dc.replace(mmd[0],valid=False,value=None)
        self.assertEqual(h.align(SPEC,key,seq,(invalid,*mmd[1:])).points[0].mmd_reason,'invalid')
        self.assertEqual(h.align(SPEC,key,(),()).points[0].sequential_reason,'missing')
        self.assertEqual(h.Schedule(horizon=100).checkpoints,())

    def test_session_context_and_detector_provenance_mismatch_rejected(self):
        key,seq,mmd=stream()
        for bad in [dc.replace(mmd[0],stream=dc.replace(key,session_id='9')),
                    dc.replace(mmd[0],stream=dc.replace(key,context=dc.replace(CONTEXT,embedding_revision='9'))),
                    dc.replace(mmd[0],revision=dc.replace(MMD,model_revision='9')),
                    dc.replace(mmd[0],revision=dc.replace(MMD,configuration_revision='9')),
                    dc.replace(mmd[0],revision=dc.replace(MMD,calibration_provenance='9'))]:
            with self.assertRaises(ValueError):h.align(SPEC,key,seq,(bad,*mmd[1:]))

    def test_duplicates_noncausal_windows_and_nonfinite_rejected(self):
        key,seq,mmd=stream()
        for windows in [(mmd[0],*mmd),(dc.replace(mmd[0],start=1),*mmd[1:])]:
            with self.assertRaises(ValueError):h.align(SPEC,key,seq,windows)
        with self.assertRaises(ValueError):dc.replace(mmd[0],computed_through=200)
        with self.assertRaises(ValueError):h.Score(key,MMD,51,150,150,float('nan'),True)
        with self.assertRaises(ValueError):dc.replace(mmd[0],orientation='lower_is_more_anomalous')

class CalibrationTests(unittest.TestCase):
    def test_fit_calibration_disjoint_benign_and_outer_groups_unique(self):
        fit=h.fit_normalizer(SPEC,[aligned(1,'fit')])
        for inputs in [[aligned(1,'calibration')],[aligned(2,'calibration'),aligned(3,'calibration',group=2)],
                       [aligned(2,'validation')]]:
            with self.assertRaises(ValueError):h.calibrate(fit,inputs,.4)
        key,seq,mmd=stream(2,'calibration',label='attack')
        with self.assertRaises(ValueError):h.calibrate(fit,[h.align(SPEC,key,seq,mmd)],.4)

    def test_joint_calibration_includes_all_checkpoint_looks(self):
        fit=h.fit_normalizer(SPEC,[aligned(1,'fit',(0.,1.,2.,3.))])
        a=h.calibrate(fit,[aligned(2,'calibration',(0.,0.,0.,3.)),aligned(3,'calibration',(0.,0.,0.,0.))],.4)
        self.assertEqual(a.thresholds['weighted'].value,1.)
        self.assertEqual(a.thresholds['weighted'].rank,2)

    def test_small_calibration_infinity_and_ties(self):
        m=model(.05);self.assertIsNone(m.thresholds['or'].value)
        self.assertEqual(m.thresholds['or'].rank,3)
        result=h.evaluate(m,aligned(4,values=(999.,)*4),'or')
        self.assertIsNone(result.first_alert_query)
        m=model(.4);equal=aligned(4,values=(1.,)*4)
        self.assertIsNone(h.evaluate(m,equal,'weighted').first_alert_query)

    def test_raw_scores_are_mapped_before_weighted_addition(self):
        m=model();self.assertEqual(m.normalizer.transform('sequential',0.),.4)
        self.assertEqual(h.fused('weighted',.2,.8,.5),.5)
        self.assertEqual(h.fused('sequential_only',.2,None,.5),.2)
        self.assertEqual(h.fused('mmd_only',None,.8,.5),.8)

    def test_or_and_truth_tables_and_joint_threshold(self):
        for u in [.1,.9]:
            for v in [.1,.9]:
                self.assertEqual(h.fused('or',u,v,.5)>.5,(u>.5 or v>.5))
                self.assertEqual(h.fused('and',u,v,.5)>.5,(u>.5 and v>.5))
                self.assertEqual(h.decision_fusion('or',u>.5,v>.5),(u>.5 or v>.5))
                self.assertEqual(h.decision_fusion('and',u>.5,v>.5),(u>.5 and v>.5))
        self.assertIsNone(h.fused('or',None,.9,.5))
        self.assertIsNone(h.fused('and',.9,None,.5))
        self.assertIsNone(h.decision_fusion('or',None,True))
        with self.assertRaises(ValueError):h.decision_fusion('or',1,False)

    def test_calibration_refuses_missing_data_and_fit_reuse(self):
        fit=h.fit_normalizer(SPEC,[aligned(1,'fit')]);key,seq,mmd=stream(2,'calibration')
        with self.assertRaises(ValueError):h.calibrate(fit,[h.align(SPEC,key,seq,mmd[1:])],.4)
        m=model()
        with self.assertRaises(ValueError):h.evaluate(m,aligned(2),'or')

    def test_or_needs_its_own_joint_calibration(self):
        fit=h.fit_normalizer(SPEC,[aligned(1,'fit',(0.,1.,2.,3.))])
        def pair(n,s,m):
            key,seq,_=stream(n,'calibration',values=(s,)*4)
            _,_,windows=stream(n,'calibration',values=(m,)*4)
            return h.align(SPEC,key,seq,windows)
        calibrated=h.calibrate(fit,[pair(2,3.,0.),pair(3,0.,3.),pair(4,0.,0.)],.5)
        self.assertEqual(calibrated.thresholds['sequential_only'].value,.4)
        self.assertEqual(calibrated.thresholds['mmd_only'].value,.4)
        self.assertEqual(calibrated.thresholds['or'].value,1.)

    def test_and_requires_coincident_checkpoint_crossing(self):
        fit=h.fit_normalizer(SPEC,[aligned(1,'fit',(0.,1.,2.,3.))])
        key,seq,_=stream(2,'calibration',values=(3.,0.,3.,0.))
        _,_,windows=stream(2,'calibration',values=(0.,3.,0.,3.))
        calibrated=h.calibrate(fit,[h.align(SPEC,key,seq,windows)],.5)
        self.assertEqual(calibrated.thresholds['and'].value,.4)
        self.assertEqual(calibrated.thresholds['or'].value,1.)

    def test_finite_threshold_resolution_at_nineteen(self):
        fit=h.fit_normalizer(SPEC,[aligned(1,'fit')])
        rows=[aligned(n,'calibration') for n in range(2,21)]
        self.assertIsNone(h.calibrate(fit,rows[:-1],.05).thresholds['weighted'].value)
        self.assertIsNotNone(h.calibrate(fit,rows,.05).thresholds['weighted'].value)

    def test_frozen_thresholds_and_spec_mismatch(self):
        m=model()
        with self.assertRaises(TypeError):m.thresholds['or']=m.thresholds['and']
        changed=dc.replace(aligned(4),spec=dc.replace(SPEC,sequential_weight=.7))
        with self.assertRaises(ValueError):h.evaluate(m,changed,'weighted')

class TimelineTests(unittest.TestCase):
    def test_first_alert_delay_and_censoring(self):
        m=model();rows=aligned(4,values=(0.,3.,3.,3.),label='attack')
        result=h.evaluate(m,rows,'weighted',attack_onset=180)
        self.assertEqual(result.first_alert_query,200);self.assertEqual(result.detection_delay,20)
        self.assertFalse(result.pre_attack_alarm);self.assertIsNone(result.censor_query)
        censored=h.evaluate(m,aligned(4,label='attack'),'or',attack_onset=180)
        self.assertEqual(censored.censor_query,300);self.assertIsNone(censored.detection_delay)

    def test_pre_attack_alarm_and_native_onset_one(self):
        m=model();rows=aligned(4,values=(3.,)*4,label='attack')
        prefix=h.evaluate(m,rows,'or',attack_onset=180)
        self.assertTrue(prefix.pre_attack_alarm);self.assertIsNone(prefix.detection_delay)
        self.assertIsNone(h.evaluate(m,rows,'or',attack_onset=1).pre_attack_alarm)

    def test_incomplete_stream_not_silently_true_negative(self):
        m=model();key,seq,mmd=stream(4,values=(0.,3.,3.,3.))
        result=h.evaluate(m,h.align(SPEC,key,seq,mmd[1:]),'or')
        self.assertFalse(result.complete);self.assertEqual(result.first_observed_alert,200)
        self.assertIsNone(result.first_alert_query);self.assertIsNone(result.detection_delay)
        counts=h.false_alarm_counts([result]);self.assertEqual(counts['incomplete'],1)
        self.assertIsNone(counts['conditional_complete_stream_fpr'])

    def test_stream_false_alarm_counts_once_and_refuses_permutation_pseudoreplication(self):
        m=model();a=h.evaluate(m,aligned(4,values=(3.,)*4),'or');b=h.evaluate(m,aligned(5),'or')
        counts=h.false_alarm_counts([a,b]);self.assertEqual(counts['false_alarm_streams'],1)
        self.assertEqual(counts['complete_streams'],2);self.assertEqual(counts['conditional_complete_stream_fpr'],.5)
        with self.assertRaises(ValueError):h.false_alarm_counts([a,a])
        with self.assertRaises(ValueError):h.false_alarm_counts([a,dc.replace(a,stream=dc.replace(a.stream,outer_group='9'))])

    def test_component_baseline_can_remain_valid_while_joint_abstains(self):
        m=model();key,seq,windows=stream(4)
        rows=h.align(SPEC,key,seq,windows[1:])
        self.assertTrue(h.evaluate(m,rows,'sequential_only').complete)
        self.assertFalse(h.evaluate(m,rows,'or').complete)

    def test_benign_onset_and_mixed_fpr_methods_are_rejected(self):
        m=model()
        with self.assertRaises(ValueError):h.evaluate(m,aligned(4),'or',attack_onset=180)
        with self.assertRaises(ValueError):h.false_alarm_counts([
            h.evaluate(m,aligned(4),'or'),h.evaluate(m,aligned(5),'and')])

if __name__=='__main__':unittest.main()
