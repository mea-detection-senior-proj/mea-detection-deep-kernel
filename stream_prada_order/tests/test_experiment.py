import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'stream_prada_order'))
sys.path.insert(0, str(ROOT / 'PRADA'))
import experiment as exp
import prada_stream_detector as official


class ProtocolTests(unittest.TestCase):
    def test_relative_config_provenance_matches_absolute_path(self):
        relative = Path('stream_prada_order/config_25min.json')
        self.assertEqual(exp.source_file_hashes([relative]),
                         exp.source_file_hashes([ROOT / relative]))

    def test_json_artifacts_use_canonical_lf_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'artifact.json'
            exp.json_write(path, {'value': [1, 2]})
            self.assertNotIn(b'\r', path.read_bytes())

    def test_orders_preserve_membership_prefix_and_onset(self):
        prefix, benign, attack = np.arange(110), np.arange(110, 192), np.arange(192, 256)
        for seed in range(5):
            orders = exp.make_orders(prefix, benign, attack, np.random.default_rng(seed))
            for order in orders.values():
                np.testing.assert_array_equal(order[:110], prefix)
                self.assertEqual(len(set(order)), 256)
                self.assertEqual(set(order), set(range(256)))
                self.assertIn(order[110], attack)
            labels = np.isin(orders['clustered'][110:], attack)
            self.assertTrue(labels[:64].all())
            self.assertFalse(labels[64:].any())

    def test_warmup_and_strict_threshold(self):
        matrix = np.zeros((103, 103), dtype=np.float32)
        self.assertEqual(exp.trace(matrix[:101, :101], np.arange(101))['w'], [])
        result = exp.trace(matrix, np.arange(103))
        self.assertEqual(result['w_steps'], [102, 103])
        self.assertEqual(result['growing'], [0])
        self.assertEqual(exp.alert(result, 0.0), False)
        self.assertIsNone(exp.first_alert(result, 0.0))

    def test_reference_parity_precomputed_and_direct(self):
        official.np = np
        official.torch = torch
        official.base.np = np
        torch.set_num_threads(1)
        for seed in range(4):
            z = np.random.default_rng(seed).normal(size=(180, 12)).astype(np.float32)
            if seed == 1:
                z[70:100] = z[0]
            for precompute in (True, False):
                zt = torch.from_numpy(z)
                # The upstream modes differ numerically on duplicate embeddings:
                # cdist uses a matrix product; direct mode uses vector differences.
                matrix = (torch.cdist(zt, zt) if precompute else
                          torch.linalg.norm(zt[:, None, :] - zt[None, :, :], dim=2)).numpy()
                actual = exp.trace(matrix, np.arange(len(z)))
                expected = official.prada_stream_trace(z, 'l2', 'cpu', .99, 100, 5000, 1,
                                                       precompute, False, np.random.default_rng(9))
                np.testing.assert_allclose(actual['w'], expected[4], atol=2e-5, rtol=0)
                self.assertAlmostEqual(actual['score'], 1 - expected[0], places=5)
                self.assertEqual(len(actual['distances']), expected[2])
                self.assertEqual(len(actual['growing']), expected[3])
                self.assertEqual(exp.first_alert(actual, 1 - .99),
                                 None if expected[1] < 0 else expected[1])

    def test_adaptive_threshold_never_decreases(self):
        z = torch.from_numpy(np.random.default_rng(3).normal(size=(160, 8)).astype(np.float32))
        result = exp.trace(torch.cdist(z, z).numpy(), np.arange(len(z)))
        self.assertTrue(np.all(np.diff(result['thresholds']) >= 0))
        self.assertEqual(len(result['distances']), 159)
        self.assertEqual(len(result['w']), 59)

    def test_resource_gate_projects_full_work(self):
        self.assertGreater(exp.project_seconds(10, 20, 10000, 1000), 1200)
        self.assertLess(exp.project_seconds(10, .02, 10000, 1000), 1200)

    def test_invalid_inputs_fail_closed(self):
        with self.assertRaises(ValueError):
            exp.trace(np.full((102, 102), np.nan), np.arange(102))
        with self.assertRaises(ValueError):
            exp.make_orders(np.arange(3), np.arange(2, 5), np.arange(5, 7), np.random.default_rng(1))


if __name__ == '__main__':
    unittest.main()
