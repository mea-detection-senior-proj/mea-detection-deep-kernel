"""Numerical reference, leakage, calibration and complete runner checks."""
import csv
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
import torch

from data_pipeline.datasets import normalize, split_rows
from data_pipeline.windows import attacker_count, make_windows
from detectors.mmd.detector import MMDDetector, mmd2_unbiased
from evaluation.windows import evaluate
from experiments.run import load_config, run


class MMDTests(unittest.TestCase):
    def test_matches_scalar_reference_and_original(self):
        from MMD_detection import mmd_detector_gpu as original
        original.np, original.torch = np, torch
        x = torch.tensor([[0., 1.], [2., 3.], [1., 4.]], dtype=torch.float64)
        y = torch.tensor([[3., 2.], [4., 5.], [6., 1.], [2., 0.]], dtype=torch.float64)
        for bandwidths in ((1.3,), (.65, 1.3, 2.6, 5.2)):
            def kernel(a, b):
                return np.mean([np.exp(-sum((float(u) - float(v))**2 for u, v in zip(a, b)) / (2 * s*s)) for s in bandwidths])
            expected = (sum(kernel(a, b) for i, a in enumerate(x) for j, b in enumerate(x) if i != j) / 6
                        + sum(kernel(a, b) for i, a in enumerate(y) for j, b in enumerate(y) if i != j) / 12
                        - 2 * sum(kernel(a, b) for a in x for b in y) / 12)
            self.assertAlmostEqual(float(mmd2_unbiased(x, y, bandwidths)), expected, places=12)
            self.assertAlmostEqual(float(mmd2_unbiased(x, y, bandwidths)), original.mmd2_unbiased(x, y, bandwidths), places=12)

    def test_repeated_score_is_mean_of_reference_scores(self):
        z = torch.tensor([[0.], [1.], [2.], [5.], [8.], [9.]], dtype=torch.float64)
        refs = torch.tensor([[0, 1], [2, 3]])
        detector = MMDDetector((2.,))
        expected = (mmd2_unbiased(z[refs[0]], z[4:], (2.,)) + mmd2_unbiased(z[refs[1]], z[4:], (2.,))) / 2
        self.assertAlmostEqual(detector.score(z, z[4:], refs), float(expected))
        with self.assertRaises(ValueError):
            MMDDetector((0.,))


class ProtocolTests(unittest.TestCase):
    def test_transitive_groups_and_cross_label_ambiguity(self):
        benign = [{"id": f"b{i}", "query": f"normal {i}"} for i in range(100)]
        attack = [{"id": f"a{i}", "query": f"attack {i}"} for i in range(100)]
        benign += [{"id": "linked", "query": "first"}, {"id": "linked", "query": "second"},
                   {"id": "third", "query": " SECOND "}, {"id": "bad", "query": "ambiguous"}]
        attack += [{"id": "bad2", "query": " AMBIGUOUS "}]
        partitions, audit, _ = split_rows(benign, attack, 42, "id-text-only")
        owners = {}
        for part, classes in partitions.items():
            for rows in classes.values():
                for row in rows:
                    text = normalize(row["query"])
                    self.assertNotEqual(text, "ambiguous")
                    for key in (("id", row["id"]), ("text", text)):
                        self.assertEqual(owners.setdefault(key, part), part)
        self.assertEqual(owners[("text", "first")], owners[("text", "second")])
        self.assertEqual(audit["cross_label_unique_texts_removed"], 1)

    def test_context_groups_are_disjoint(self):
        attack = [{"id": str(i), "query": f"Given this context: source {i // 2} Can you answer this question briefly: q{i}"}
                  for i in range(100)]
        partitions, _, _ = split_rows([], attack, 1, "id-text-attack-context")
        owners = {}
        for part, classes in partitions.items():
            for row in classes["attack"]:
                source = row["query"].split("Can you")[0]
                self.assertEqual(owners.setdefault(source, part), part)
        with self.assertRaises(ValueError):
            split_rows([], [{"id": "x", "query": "missing source"}], 1, "id-text-attack-context")

    def test_windows_use_exact_counts_without_replacement(self):
        windows = make_windows(np.arange(100), np.arange(100, 200), np.arange(200, 300),
                               10, 3, 2, [0, .01, .25, 1], np.random.default_rng(42))
        self.assertEqual([w.attacker_count for w in windows], [0, 0, 1, 1, 3, 3, 10, 10])
        self.assertEqual(attacker_count(250, .01), 3)
        for window in windows:
            self.assertEqual(len(set(window.indices)), 10)
            self.assertEqual(sum((window.indices >= 100) & (window.indices < 200)), window.attacker_count)
            self.assertTrue((window.references >= 200).all())
            self.assertTrue(all(len(set(draw)) == 10 for draw in window.references))
        with self.assertRaises(ValueError):
            make_windows(np.arange(2), [], np.arange(10), 3, 1, 1, [0], np.random.default_rng())

    def test_calibration_and_methods_use_identical_draws(self):
        class Recorder:
            def __init__(self):
                self.calls = []
            def score(self, pool, window, refs):
                self.calls.append((window.clone(), refs.clone()))
                return float(window.mean())
        a, b = Recorder(), Recorder()
        z = torch.arange(300, dtype=torch.float64)[:, None]
        rng = np.random.default_rng(1)
        cal = make_windows(np.arange(30), [], np.arange(200, 300), 10, 3, 8, [0], rng)
        test = make_windows(np.arange(30, 100), np.arange(100, 200), np.arange(200, 300), 10, 3, 3, [0, .1], rng)
        rows, null, _, thresholds = evaluate({"a": a, "b": b}, z, cal, test, .05)
        self.assertEqual(len(a.calls), 14)
        for ca, cb in zip(a.calls, b.calls):
            self.assertTrue(torch.equal(ca[0], cb[0]) and torch.equal(ca[1], cb[1]))
            self.assertEqual(tuple(ca[1].shape), (3, 10))
        expected = np.quantile([r["score"] for r in null if r["method"] == "a"], .95, method="higher")
        self.assertEqual(thresholds["a"], expected)
        self.assertTrue(all(r["suspicious"] == int(r["score"] > r["threshold"]) for r in rows))


class RunnerTests(unittest.TestCase):
    def test_end_to_end_manifest_reproducibility_and_no_overwrite(self):
        temporary_root = Path(__file__).resolve().parents[1] / "artifacts" / "test_tmp"
        temporary_root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=temporary_root) as folder:
            root = Path(folder)
            for label in ("benign", "attack"):
                rows = [{"id": f"{label}-{i}", "query": f"{label} example {i}"} for i in range(300)]
                (root / f"{label}.jsonl").write_text("\n".join(json.dumps(row) for row in rows), encoding="utf-8")
            spec = {"name": "fixture", "benign_path": "benign.jsonl", "attack_path": "attack.jsonl",
                    "grouping_policy": "id-text-only", "provenance_notes": "Synthetic test data"}
            (root / "dataset.json").write_text(json.dumps(spec))
            config = {"dataset_config": str(root / "dataset.json"), "data_root": str(root),
                      "embedding_model": str(root), "output": str(root / "run1"), "seeds": [42],
                      "window_sizes": [10], "attacker_ratios": [.01, .25, 1],
                      "reference_repeats": 2, "calibration_windows": 4, "test_windows": 2}
            config_path = root / "config.json"
            config_path.write_text(json.dumps(config))
            def fake_encoder(texts, *args):
                z = np.asarray([[len(text), sum(map(ord, text)) % 97] for text in texts], dtype=np.float32)
                return z, {"fixture": True}
            with patch("experiments.run.embed_texts", side_effect=fake_encoder):
                resolved = load_config(config_path)
                first = run(resolved)
                with self.assertRaises(FileExistsError):
                    run(resolved)
                second = run({**resolved, "output": str(root / "run2")})
            for name in ("summary.csv", "seed_42/split_manifest.json", "seed_42/window_10/scores.csv",
                         "seed_42/window_10/draw_manifest.json"):
                self.assertEqual((first / name).read_bytes(), (second / name).read_bytes())
            meta = json.loads((first / "metadata.json").read_text())
            self.assertEqual(meta["status"], "complete")
            with (first / "summary.csv").open() as stream:
                self.assertEqual(len(list(csv.DictReader(stream))), 8)
            config_path.write_text(json.dumps({**config, "reference_repeats": 0}))
            with self.assertRaises(ValueError):
                load_config(config_path)
            config_path.write_text(json.dumps({**config, "typo": 123}))
            with self.assertRaises(ValueError):
                load_config(config_path)
            config_path.write_text(json.dumps({**config, "embedding_model": "remote/model"}))
            with self.assertRaises(ValueError):
                load_config(config_path)


if __name__ == "__main__":
    unittest.main()
