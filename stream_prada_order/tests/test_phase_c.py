import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import phase_c_runner as pc


class PhaseCTests(unittest.TestCase):
    def test_benign_control_alarm_is_never_an_attack_detection(self):
        tr={'w_steps':[102,113,256],'w':[.99,.8,.97],'score':.2,'growing':[0],'distances':[1.0]*255}
        row=pc.score_row(tr,.1,110,has_attack=False)
        self.assertTrue(row['any_alert'])
        self.assertIsNone(row['post_onset_first_detection'])
        self.assertIsNone(row['delay'])
        self.assertIsNone(row['at_risk_at_onset'])

    def test_shared_prefix_onset_and_nested_membership_across_ratios(self):
        cfg={'seed':20261107,'prefix_length':110,'stream_length':256,'attack_counts':[26,64,128]}
        plan=pc.plan_cohort(14,256,128,cfg)
        sets=[]
        for ri,count in enumerate(cfg['attack_counts']):
            orders=pc.orders_for(plan,14,ri,3,cfg)
            for order in orders.values():
                np.testing.assert_array_equal(order[:110],plan['benign_order'][:110])
                self.assertGreaterEqual(order[110],256)
                self.assertEqual(np.sum(order>=256),count)
                self.assertEqual(len(set(order)),256)
            sets.append(set(orders['random'][orders['random']>=256]))
        self.assertTrue(sets[0]<sets[1]<sets[2])

    def test_schedule_is_reproducible(self):
        cfg={'seed':7,'prefix_length':110,'stream_length':256,'attack_counts':[26,64,128]}
        p=pc.plan_cohort(1,256,128,cfg)
        for key,a in pc.orders_for(p,1,0,9,cfg).items():
            np.testing.assert_array_equal(a,pc.orders_for(p,1,0,9,cfg)[key])

    def test_prefix_alarm_is_ineligible_not_attack_detection(self):
        tr={'w_steps':[102,111,120],'w':[.8,.79,.95],'score':.21,'growing':[0],'distances':[1.0]*255}
        row=pc.score_row(tr,.1,110)
        self.assertTrue(row['prefix_alarm'])
        self.assertFalse(row['at_risk_at_onset'])
        self.assertIsNone(row['delay'])
        self.assertFalse(row['right_censored'])

    def test_missed_detection_is_right_censored(self):
        tr={'w_steps':[102,111,256],'w':[.99,.98,.97],'score':.03,'growing':[0],'distances':[1.0]*255}
        row=pc.score_row(tr,.1,110)
        self.assertTrue(row['at_risk_at_onset'])
        self.assertTrue(row['right_censored'])
        self.assertIsNone(row['delay'])

    def test_onset_alert_has_zero_delay(self):
        tr={'w_steps':[102,111,256],'w':[.99,.89,.97],'score':.11,'growing':[0],'distances':[1.0]*255}
        self.assertEqual(pc.score_row(tr,.1,110)['delay'],0)

    def test_validation_failure_closes_evaluation_gate(self):
        cfg={'validation_max_control_alerts':0,'validation_max_prefix_alerts':0}
        self.assertFalse(pc.validation_passes([{'any_alert':True,'prefix_alarm':False}],cfg))
        self.assertFalse(pc.validation_passes([{'any_alert':False,'prefix_alarm':True}],cfg))
        self.assertTrue(pc.validation_passes([{'any_alert':False,'prefix_alarm':False}],cfg))

    def test_strict_threshold_tie_has_no_alarm(self):
        tr={'w_steps':[102],'w':[.875],'score':.125,'growing':[0],'distances':[1.0]*101}
        self.assertFalse(pc.score_row(tr,.125,110)['any_alert'])

    def test_zero_event_interval_keeps_uncertainty(self):
        low,high=pc.exact_interval(0,8)
        self.assertEqual(low,0)
        self.assertGreater(high,.3)


if __name__=='__main__': unittest.main()
