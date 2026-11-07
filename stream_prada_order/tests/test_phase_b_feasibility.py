import sys
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'stream_prada_order'))
import phase_b_feasibility as fb


def group(name,b,a=0):
    return {'id':name,'B':[f'{name}b{i}' for i in range(b)],'A':[f'{name}a{i}' for i in range(a)],'known_article':True}


class FeasibilityTests(unittest.TestCase):
    def test_context_wrapper_removal_preserves_original_quote(self):
        self.assertEqual(fb.model_passage('Given this context: "123""\n Can you answer this question briefly: 456'),'123"')

    def test_oversize_source_cannot_be_split_across_cohorts(self):
        gs=[group('x',600,600)]
        cohorts,left=fb.allocate(gs,[(256,0)]*3)
        self.assertEqual(len(cohorts),1)
        self.assertEqual(fb.upper_bound(gs,256,0),1)

    def test_exact_subset_construction_reaches_bound(self):
        gs=[group('a',128),group('b',128),group('c',256)]
        cohorts,_=fb.allocate(gs,[(256,0)]*2)
        self.assertEqual(len(cohorts),2)
        fb.validate_allocation(cohorts)

    def test_calibration_and_mixed_cohorts_do_not_share_groups(self):
        gs=[group(str(i),256) for i in range(4)]+[group('a'+str(i),0,128) for i in range(2)]
        cohorts,_=fb.allocate(gs,[(256,0),(256,0),(256,128),(256,128)])
        self.assertEqual(len(cohorts),4)
        fb.validate_allocation(cohorts)

    def test_bad_certificate_is_rejected(self):
        cohorts=[{'groups':['g'],'B':['x'],'A':[],'required_B':1,'required_A':0}]*2
        with self.assertRaises(ValueError): fb.validate_allocation(cohorts)

    def test_boolq_requires_passage_and_question_delimiter(self):
        self.assertEqual(fb.boolq_passage('Passage: 123\nQuestion: 456'),'123')
        with self.assertRaises(ValueError): fb.boolq_passage('123')

    def test_zero_false_positive_bound_requires_59_trials(self):
        self.assertGreater(fb.zero_fp_upper(58),.05)
        self.assertLess(fb.zero_fp_upper(59),.05)

    def test_unknown_article_is_not_certified(self):
        gs=[group('a',256),{**group('u',256),'known_article':False}]
        self.assertEqual(len(fb.eligible_groups(gs,strict=True)),1)


if __name__=='__main__': unittest.main()
