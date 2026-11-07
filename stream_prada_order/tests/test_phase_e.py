"""Numeric controls and integrity fixtures for Phase E diagnostics."""
import sys
from pathlib import Path
import unittest
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import phase_e_analysis as e


class ShortcutControlTests(unittest.TestCase):
    def test_endpoint_length_is_invariant_to_order(self):
        x=np.arange(256)+1
        self.assertEqual(e.length_endpoint(x)[0],[256])
        self.assertAlmostEqual(e.length_endpoint(x)[1][0],e.length_endpoint(x[::-1])[1][0])

    def test_distance_endpoint_is_bag_statistic(self):
        d=np.linspace(.1,1,255)
        self.assertAlmostEqual(e.distance_endpoint(d)[1][0],-np.mean(d[100:]))
        swapped=d.copy(); swapped[100:]=swapped[100:][::-1]
        self.assertAlmostEqual(e.distance_endpoint(d)[1][0],e.distance_endpoint(swapped)[1][0])

    def test_surrogate_preserves_prefix_and_suffix_bag(self):
        z=np.arange(255,dtype=float)
        for name in ['reverse','shuffle17','shuffle29']:
            changed=e.surrogate(z,name)
            np.testing.assert_array_equal(changed[:109],z[:109])
            np.testing.assert_array_equal(np.sort(changed[109:]),z[109:])
            np.testing.assert_array_equal(changed,e.surrogate(z,name))

    def test_prefix_center_uses_no_future_observations(self):
        z=np.arange(255,dtype=float)
        changed=z.copy(); changed[100:]+=999
        self.assertEqual(e.prefix_center(z)[0],e.prefix_center(changed)[0])
        self.assertAlmostEqual(np.mean(e.prefix_center(z)[:100]),0)

    def test_growth_reconstruction_strict_admission(self):
        g=e.reconstruct_growth([1.,1.,.1])
        self.assertEqual(g['admitted'],[True,True,True,False])
        self.assertEqual(g['counts'],[1,2,3,3])
        self.assertTrue(np.all(np.diff(g['thresholds'])>=0))

    def test_length_regression_is_position_demeaned(self):
        u=np.tile(np.linspace(1,2,255),(4,1))+np.arange(4)[:,None]*.1
        d=np.linspace(.5,1,255)[None,:]+.25*u
        fit=e.fit_length(d,u,.01)
        self.assertAlmostEqual(fit['beta'],.25)
        np.testing.assert_allclose(fit['sigma'],.01)

    def test_length_control_caps_extrapolation_and_flags_support(self):
        u=np.array([1.,2.,3.]); fit={'support':[1.,2.],'beta':2.,'u_mean':[1.]*3}
        np.testing.assert_allclose(e.adjust_length(np.ones(3)*5,u,fit),[5,3,3])
        np.testing.assert_array_equal(e.in_support(u,fit['support']),[True,True,False])

    def test_no_length_overlap_has_zero_match_capacity(self):
        overlap=e.overlap_counts([3,7],[128,256],[0,8,16,32,64,128,256])
        self.assertEqual(overlap['matched_pair_capacity'],0)

    def test_leave_one_cohort_out_does_not_reweight_by_permutations(self):
        rows=[{'cohort':12,'rate':1.},{'cohort':13,'rate':0.},{'cohort':14,'rate':0.}]
        self.assertEqual(e.leave_one_out(rows),[0.,.5,.5])

    def test_constant_correlation_is_null(self):
        self.assertIsNone(e.rho(np.ones(10),np.arange(10)))

    def test_surrogate_delay_is_not_reported_as_real_query_delay(self):
        row=e.metric_row([102,120],[0,2],{'finite':True,'threshold':1},True,True)
        self.assertIsNone(row['delay']); self.assertEqual(row['surrogate_delay'],9)


if __name__=='__main__': unittest.main()
