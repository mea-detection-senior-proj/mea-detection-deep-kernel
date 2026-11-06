import sys
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'stream_prada_order'))
import failure_analysis as fa


class FailureAnalysisTests(unittest.TestCase):
    def test_strict_alert_and_warmup_step_are_preserved(self):
        trace = {'w_steps': [102, 103, 104], 'w': [.875, .874, .9]}
        self.assertEqual(fa.first_crossing(trace, .125), 103)
        self.assertIsNone(fa.first_crossing(trace, .2))
        self.assertIsNone(fa.first_crossing(trace, .125, horizon=102))

    def test_horizon_scores_use_only_available_history(self):
        trace = {'w_steps': [102, 103, 104], 'w': [.98, .9, .96]}
        self.assertEqual(fa.horizon_score(trace, 101), 0)
        self.assertAlmostEqual(fa.horizon_score(trace, 102), .02)
        self.assertAlmostEqual(fa.horizon_score(trace, 103), .1)
        self.assertAlmostEqual(fa.horizon_score(trace, 104), .1)

    def test_components_are_transitive_across_key_types(self):
        keys = [[('id', 1), ('text', 11)], [('id', 1), ('context', 9)],
                [('context', 9), ('text', 22)], [('id', 4)]]
        groups = fa.connected_components(keys)
        self.assertEqual(groups[0], groups[2])
        self.assertNotEqual(groups[0], groups[3])

    def test_composition_distinguishes_rows_from_independent_groups(self):
        result = fa.composition([1, 1, 1, 2])
        self.assertEqual(result['queries'], 4)
        self.assertEqual(result['source_groups'], 2)
        self.assertAlmostEqual(result['largest_group_fraction'], .75)
        self.assertAlmostEqual(result['effective_groups_hhi'], 1/.625)

    def test_saved_score_match_is_a_hard_gate(self):
        trace = {'w_steps': [102, 103], 'w': [.98, .85], 'score': .15}
        fa.check_replay(.15, True, trace, .125)
        with self.assertRaises(ValueError):
            fa.check_replay(.14, True, trace, .125)
        with self.assertRaises(ValueError):
            fa.check_replay(.15, False, trace, .125)

    def test_percentile_exceedance_is_in_sample_not_validation(self):
        scores = np.arange(200, dtype=float)/1000
        threshold = float(np.percentile(scores, 95))
        self.assertEqual(fa.score_distribution(scores, threshold)['exceedances'], 10)

    def test_missing_benign_timing_is_not_invented(self):
        inventory = fa.timing_inventory([{'stream': '0', 'score': '.1', 'alert': 'True'}])
        self.assertFalse(inventory['first_alert_saved'])
        self.assertIsNone(inventory['first_alert_steps'])


if __name__ == '__main__':
    unittest.main()
