import unittest

import numpy as np
import torch
from torch import nn

from MMD_detection import mmd_detector_gpu as original
from pilot.deep_kernel_pilot import draw_reference_indices, fit_kernel, mmd, repeated_score


class TrainingTests(unittest.TestCase):
    def test_repeated_reference_score_is_mean_of_shared_draws(self):
        torch.manual_seed(10)
        pool = torch.randn(50, 4)
        window = torch.randn(12, 4)
        indices = draw_reference_indices(pool, 12, 4, np.random.default_rng(42))
        expected = torch.stack([mmd(pool[index], window, [1., 2.]) for index in indices]).mean()
        self.assertTrue(torch.allclose(repeated_score(pool, indices, window, [1., 2.], None), expected))
        self.assertEqual(len({tuple(row.tolist()) for row in indices}), 4)

    def test_fixed_kernel_matches_repository(self):
        torch.manual_seed(1)
        x = torch.randn(13, 5, dtype=torch.float64)
        y = torch.randn(11, 5, dtype=torch.float64)
        sigmas = [.5, 1., 2., 4.]
        self.assertAlmostEqual(mmd(x, y, sigmas).item(), original.mmd2_unbiased(x, y, sigmas), places=12)

    def test_learned_kernel_gradient_matches_finite_difference(self):
        torch.manual_seed(2)
        x = torch.randn(12, 4, dtype=torch.float64)
        y = torch.randn(12, 4, dtype=torch.float64) + .5
        network = nn.Linear(4, 3, bias=False, dtype=torch.float64)
        loss = mmd(x, y, [1., 2.], network)
        loss.backward()
        analytical = network.weight.grad[0, 0].item()
        with torch.no_grad():
            weight = network.weight[0, 0]
            weight.add_(1e-5)
            plus = mmd(x, y, [1., 2.], network).item()
            weight.sub_(2e-5)
            minus = mmd(x, y, [1., 2.], network).item()
            weight.add_(1e-5)
        self.assertGreater(abs(analytical), 1e-8)
        self.assertAlmostEqual(analytical, (plus - minus) / 2e-5, places=7)

    def test_checkpoint_selected_on_fixed_validation_and_frozen(self):
        torch.manual_seed(3)
        benign_train, attack_train, benign_val, attack_val = [torch.randn(100, 4) for _ in range(4)]
        attack_train += 1
        attack_val += 1
        network = nn.Sequential(nn.Linear(4, 8), nn.ReLU(), nn.Linear(8, 3))
        result = fit_kernel(network, benign_train, attack_train, benign_val, attack_val,
                            [1., 2.], 20, 3, 4, 5,
                            np.random.default_rng(4), np.random.default_rng(5))
        candidates = [result['initial_validation_objective']] + [r['validation_objective'] for r in result['history']]
        self.assertEqual(result['best_epoch'], int(np.argmax(candidates)))
        self.assertAlmostEqual(result['best_validation_objective'], max(candidates))
        self.assertTrue(all(not p.requires_grad for p in network.parameters()))
        self.assertFalse(network.training)
        self.assertTrue(all(np.isfinite(r['gradient_norm']) for r in result['history']))
        self.assertTrue(any(r['gradient_norm'] > 0 for r in result['history']))


if __name__ == '__main__':
    unittest.main()
