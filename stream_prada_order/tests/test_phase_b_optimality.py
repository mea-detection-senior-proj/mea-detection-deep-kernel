import sys
from pathlib import Path
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from phase_b_optimality import prove_capacity


class ProofTests(unittest.TestCase):
    def test_three_small_groups_cannot_cover_two_cohorts(self):
        groups=[{'id':str(i),'B':[f'{i}a',f'{i}b'],'A':[]} for i in range(3)]
        proof=prove_capacity(groups,3,0,1,2)
        self.assertEqual(proof['status'],'optimal_certified')
        self.assertEqual(proof['upper'],1)


if __name__=='__main__': unittest.main()
