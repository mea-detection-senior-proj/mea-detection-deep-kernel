"""Kernel/objective numerical checks, gradients, checkpoint selection and locked runs."""
import csv
import json
import math
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
import torch

from detectors.deep_kernel_mmd.model import DeepKernelMMD
from detectors.deep_kernel_mmd.training import fit_kernel, load_detector, power_objective
from experiments.locked import load_draws, prepare, verify_lock
from experiments.run import load_config, run
from experiments.summarize_comparison import summarize


class DeepKernelTests(unittest.TestCase):
    def setUp(self):
        torch.manual_seed(123)
        self.model = DeepKernelMMD(3, 1.2, 4, 2).double()
        self.x = torch.randn(6, 3, dtype=torch.float64)
        self.y = torch.randn(6, 3, dtype=torch.float64) + 1

    def test_kernel_matches_equation_and_is_positive_semidefinite(self):
        h = self.model.network(self.x).detach().numpy()
        x = self.x.numpy()
        expected = np.empty((6, 6))
        for i in range(6):
            for j in range(6):
                feature = math.exp(-sum((h[i] - h[j])**2) / 2)
                base = math.exp(-sum((x[i] - x[j])**2) / (2 * float(self.model.log_base_bandwidth.detach().exp())**2))
                expected[i, j] = (.9 * feature + .1) * base
        actual = self.model.kernel(self.x, self.x).detach().numpy()
        np.testing.assert_allclose(actual, expected, atol=1e-12)
        self.assertGreater(np.linalg.eigvalsh(actual).min(), -1e-10)

    def test_objective_matches_scalar_variance_formula(self):
        kxx, kyy, kxy = [k.detach().numpy() for k in (self.model.kernel(self.x, self.x),
                                                    self.model.kernel(self.y, self.y), self.model.kernel(self.x, self.y))]
        h = kxx + kyy - kxy - kxy.T
        n = len(h)
        numerator = sum(h[i, j] for i in range(n) for j in range(n) if i != j) / (n * (n - 1))
        variance = 4 / n**3 * sum(sum(h[i, j] for j in range(n))**2 for i in range(n)) - 4 / n**4 * sum(h.flatten())**2
        value, observed, estimated = power_objective(self.model, self.x, self.y, 1e-8)
        self.assertAlmostEqual(float(observed.detach()), numerator, places=12)
        self.assertAlmostEqual(float(estimated.detach()), variance, places=12)
        self.assertAlmostEqual(float(value.detach()), numerator / math.sqrt(variance + 1e-8), places=12)

    def test_autograd_matches_finite_differences_and_parameter_gradients(self):
        x, y = self.x.clone().requires_grad_(), self.y.clone().requires_grad_()
        self.assertTrue(torch.autograd.gradcheck(lambda a, b: power_objective(self.model, a, b, 1e-8)[0],
                                                (x, y), eps=1e-6, atol=1e-5, rtol=1e-4))
        power_objective(self.model, x, y, 1e-8)[0].backward()
        for parameter in self.model.parameters():
            self.assertIsNotNone(parameter.grad)
            self.assertTrue(torch.isfinite(parameter.grad).all())
            self.assertGreater(float(parameter.grad.abs().sum()), 0)

    def test_validation_selects_and_freezes_checkpoint(self):
        benign, attack = torch.randn(30, 3, dtype=torch.float64), torch.randn(30, 3, dtype=torch.float64) + 1
        result = fit_kernel(self.model, benign[:15], attack[:15], benign[15:], attack[15:],
                            {"window_size": 4, "epochs": 2, "steps_per_epoch": 2, "validation_pairs": 3}, 42)
        self.assertEqual(result["best_validation_objective"], max([result["initial_validation_objective"]]
                         + [row["validation_objective"] for row in result["history"]]))
        self.assertFalse(self.model.training)
        self.assertTrue(all(not parameter.requires_grad for parameter in self.model.parameters()))
        refs = torch.tensor([[0, 1, 2, 3], [4, 5, 6, 7]])
        score = self.model.score(benign, attack[:4], refs)
        expected = []
        for indices in refs:
            xx, yy, xy = self.model.kernel(benign[indices], benign[indices]), self.model.kernel(attack[:4], attack[:4]), self.model.kernel(benign[indices], attack[:4])
            expected.append((xx.sum() - xx.trace()) / 12 + (yy.sum() - yy.trace()) / 12 - 2 * xy.mean())
        self.assertAlmostEqual(score, float(torch.stack(expected).mean()), places=12)


class LockedRunTests(unittest.TestCase):
    def test_prepared_draws_are_shared_and_tampering_rejected(self):
        temp_root = Path(__file__).resolve().parents[1] / "artifacts" / "test_tmp"
        temp_root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=temp_root) as folder:
            root = Path(folder)
            for label in ("benign", "attack"):
                entries = [{"id": f"{label}{i}", "query": f"{label} example {i}"} for i in range(100)]
                (root / f"{label}.jsonl").write_text("\n".join(json.dumps(row) for row in entries))
            spec = {"name": "fixture", "benign_path": "benign.jsonl", "attack_path": "attack.jsonl",
                    "grouping_policy": "id-text-only", "provenance_notes": "Synthetic"}
            (root / "dataset.json").write_text(json.dumps(spec))
            config = {"dataset_config": str(root / "dataset.json"), "data_root": str(root), "embedding_model": str(root),
                      "output": str(root / "baseline"), "protocol_lock": str(root / "lock"), "device": "cpu", "dtype": "float64",
                      "seeds": [42], "window_sizes": [4], "attacker_ratios": [.25, 1], "reference_repeats": 2,
                      "calibration_windows": 4, "test_windows": 2,
                      "training": {"window_size": 4, "epochs": 1, "steps_per_epoch": 1, "validation_pairs": 2, "hidden_dim": 4, "feature_dim": 2}}
            (root / "config.json").write_text(json.dumps(config))
            config = load_config(root / "config.json")
            def fake_encode(texts, *args):
                return np.random.default_rng(1).normal(size=(len(texts), 3)).astype(np.float32), {"fixture": True}
            with patch("experiments.locked.embed_texts", side_effect=fake_encode):
                lock = prepare(config, root / "lock")
            baseline = run(config)
            deep = run({**config, "methods": ["deep_kernel"], "output": str(root / "deep")})
            a, b = [json.loads((path / "metadata.json").read_text()) for path in (baseline, deep)]
            self.assertEqual(a["status"], "complete")
            self.assertEqual(b["status"], "complete")
            self.assertEqual(a["lock_id"], b["lock_id"])
            self.assertEqual(a["cases"], b["cases"])
            report = summarize([baseline, deep], root / "comparison")
            self.assertTrue((report / "overall.csv").is_file())
            checkpoint = torch.load(deep / "seed_42/deep_kernel.pt", map_location="cpu", weights_only=True)
            replay = load_detector(deep / "seed_42/deep_kernel.pt")
            self.assertFalse(replay.training)
            self.assertTrue(all(not p.requires_grad for p in replay.parameters()))
            self.assertEqual(next(replay.parameters()).dtype, torch.float64)
            embeddings = torch.as_tensor(np.load(lock / "embeddings.npy"), dtype=torch.float64)
            _, windows = load_draws(lock / "seed_42/window_4.npz")
            with (deep / "seed_42/window_4/scores.csv").open(newline="") as stream:
                scores = list(csv.DictReader(stream))
            for row, window in zip(scores, windows):
                self.assertEqual(replay.score(embeddings, embeddings[window.indices],
                                             torch.as_tensor(window.references)), float(row["score"]))
            self.assertEqual(checkpoint["lock_id"], a["lock_id"])
            with patch.dict(b, {"cases": []}):
                (deep / "metadata.json").write_text(json.dumps(b))
                with self.assertRaisesRegex(ValueError, "differ"):
                    summarize([baseline, deep], root / "bad_comparison")
            with self.assertRaises(ValueError):
                verify_lock(lock, {**config, "reference_repeats": 3})
            with (lock / "seed_42/window_4.npz").open("ab") as stream:
                stream.write(b"tampered")
            with self.assertRaisesRegex(ValueError, "modified"):
                verify_lock(lock, config)


if __name__ == "__main__":
    unittest.main()
