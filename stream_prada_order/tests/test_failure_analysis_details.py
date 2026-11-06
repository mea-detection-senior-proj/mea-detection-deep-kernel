import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'stream_prada_order'))
import failure_analysis_details as details


class DetailTests(unittest.TestCase):
    def test_transient_crossing_is_not_erased_by_recovery(self):
        trace={'stream':2,'w_steps':[102,103,256],'w':[.86,.9,.97],
               'distances':[1.0]*255,'score':.14,'kept_shapiro_samples':[101,102,255]}
        row=details.trace_details(trace,.125)
        self.assertEqual(row['first_alert'],102)
        self.assertTrue(row['final_w_recovered'])
        self.assertFalse(row['final_w_below_threshold'])
        self.assertEqual(row['minimum_w_step'],102)

    def test_no_alert_has_no_recovery_or_first_sample_count(self):
        trace={'stream':1,'w_steps':[102,256],'w':[.98,.99],
               'distances':[1.0]*255,'score':.02,'kept_shapiro_samples':[101,255]}
        row=details.trace_details(trace,.125)
        self.assertIsNone(row['first_alert'])
        self.assertFalse(row['final_w_recovered'])
        self.assertIsNone(row['kept_at_first_alert'])

    def test_degenerate_distance_skew_is_null(self):
        summary=details.distance_details([1.0]*101)
        self.assertIsNone(summary['filtered_skew'])
        self.assertEqual(summary['kept_samples'],101)


if __name__=='__main__':
    unittest.main()
