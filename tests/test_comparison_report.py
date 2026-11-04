"""Exercise report integrity and empirical endpoints through completed artifact fixtures."""
import contextlib
import copy
import csv
import io
import json
from pathlib import Path
import tempfile
import unittest

import numpy as np

from data_pipeline.datasets import digest
from data_pipeline.windows import make_windows
from experiments.artifacts import write_csv, write_json
from experiments.configuration import load_config
from experiments.locked import load_draws, protocol_settings, save_draws, sha256
from experiments.summarize_comparison import summarize


METHODS = ["rbf", "multi_rbf", "deep_kernel", "learned_rbf", "mlp"]


def read_csv(path):
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


class ComparisonReportTests(unittest.TestCase):
    def setUp(self):
        parent = Path(__file__).resolve().parents[1] / "artifacts/test_tmp"
        parent.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=parent)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def make_run(self, dataset="fixture", seeds=(1,), methods=METHODS, rates=None, attacks=40):
        directory = self.root / dataset
        directory.mkdir()
        lock_path = directory / "protocol"
        lock_path.mkdir()
        config = load_config(overrides={"dataset": dataset, "embedding_model": str(self.root),
                                       "seeds": list(seeds), "window_sizes": [4, 8],
                                       "attacker_ratios": [.25, 1.], "reference_repeats": 1,
                                       "calibration_windows": 4, "test_windows": 20})
        # Reporting accepts every selected method; these are score fixtures, not trained models.
        config.update(methods=list(methods), protocol_lock=str(lock_path))
        lock = {"status": "complete", "protocol": "locked-fixed-window-v1", "settings": protocol_settings(config),
                "dataset": {"name": dataset}, "files": {}, "cases": [], "seeds": {}}
        for seed in seeds:
            attack_count = attacks[seed] if isinstance(attacks, dict) else attacks
            lock["seeds"][str(seed)] = {"sizes": {"reference": {"benign": 40}, "calibration": {"benign": 40},
                                                   "test": {"benign": 40, "attack": attack_count}}}
            seed_path = lock_path / f"seed_{seed}"
            seed_path.mkdir()
            for size in (4, 8):
                rng = np.random.default_rng(seed + size)
                calibration = make_windows(np.arange(40), [], np.arange(40), size, 1, 4, [0], rng)
                # Explicitly construct supported fixtures, including benign-only when attacks=0.
                ratios = [0] + ([.25] if attack_count >= size // 4 else []) + ([1.] if attack_count >= size else [])
                test = make_windows(np.arange(40), np.arange(40, 40 + attack_count), np.arange(40), size, 1, 20, ratios, rng)
                relative = f"seed_{seed}/window_{size}.npz"
                save_draws(lock_path / relative, calibration, test)
                lock["files"][relative] = sha256(lock_path / relative)
                lock["cases"].append({"seed": seed, "window_size": size, "draws": relative})
        lock["lock_id"] = digest(json.dumps(lock, sort_keys=True))
        write_json(lock_path / "lock.json", lock)
        output = directory / "run"
        output.mkdir()
        write_json(output / "config.json", config)
        meta = {"status": "complete", "protocol": lock["protocol"], "protocol_lock": str(lock_path),
                "lock_id": lock["lock_id"], "dataset": lock["dataset"],
                "cases": [{"seed": c["seed"], "window_size": c["window_size"],
                           "draws_sha256": lock["files"][c["draws"]]} for c in lock["cases"]]}
        write_json(output / "metadata.json", meta)
        summary = []
        for case in lock["cases"]:
            _, test = load_draws(lock_path / case["draws"])
            seed, size = case["seed"], case["window_size"]
            target = output / f"seed_{seed}/window_{size}"
            target.mkdir(parents=True)
            scores, calibration_scores = [], []
            for method in methods:
                calibration_scores.extend({"method": method, "window_id": i, "score": 0., "threshold": 0.} for i in range(4))
                for split in dict.fromkeys(w.split for w in test):
                    count = (rates or {}).get((method, seed, size, split), 1 if split == "heldout_benign" else 18)
                    for i, (index, window) in enumerate((i, w) for i, w in enumerate(test) if w.split == split):
                        scores.append({"method": method, "window_id": index, "window_size": size,
                                       "split": split, "attacker_count": window.attacker_count,
                                       "requested_ratio": window.requested_ratio, "actual_ratio": window.attacker_count / size,
                                       "score": float(i < count), "threshold": 0., "suspicious": int(i < count)})
                    summary.append({"dataset": dataset, "seed": seed, "window_size": size, "method": method,
                                    "split": split, "windows": 20, "alerts": count, "detection_rate": count / 20})
            write_csv(target / "scores.csv", scores)
            write_csv(target / "calibration_scores.csv", calibration_scores)
            write_json(target / "metadata.json", {"thresholds": {m: 0. for m in methods},
                       "draws_sha256": lock["files"][case["draws"]], "locked_draws": case["draws"]})
        write_csv(output / "summary.csv", summary)
        return output

    def report(self, runs, name="report"):
        with contextlib.redirect_stdout(io.StringIO()):
            return summarize(runs, self.root / name)

    def test_five_methods_endpoints_boundaries_and_plots(self):
        rates = {("multi_rbf", 1, 4, "heldout_benign"): 2,
                 ("multi_rbf", 1, 4, "mixed_0.25"): 20,
                 ("deep_kernel", 1, 4, "mixed_0.25"): 17,
                 ("deep_kernel", 1, 8, "mixed_0.25"): 17,
                 ("learned_rbf", 1, 4, "heldout_benign"): 2,
                 ("learned_rbf", 1, 8, "heldout_benign"): 2,
                 ("mlp", 1, 4, "mixed_0.25"): 0,
                 ("mlp", 1, 8, "mixed_0.25"): 0}
        output = self.report([self.make_run(rates=rates)])
        endpoints = {r["method"]: r for r in read_csv(output / "minimum_windows.csv") if r["split"] == "mixed_0.25"}
        self.assertEqual(endpoints["rbf"]["minimum_effective_window_size"], "4")
        self.assertEqual(endpoints["rbf"]["tpr"], "0.9")
        self.assertEqual(endpoints["rbf"]["measured_fpr"], "0.05")
        self.assertEqual(endpoints["multi_rbf"]["minimum_effective_window_size"], "8")
        self.assertEqual(endpoints["deep_kernel"]["status"], "not_reached")
        self.assertEqual(endpoints["learned_rbf"]["status"], "not_reached")
        self.assertEqual(endpoints["mlp"]["status"], "not_reached")
        self.assertEqual(endpoints["mlp"]["minimum_effective_window_size"], "")
        report = (output / "REPORT.md").read_text(encoding="utf-8")
        for method in METHODS:
            self.assertIn(method, report)
        self.assertIn("not a confidence interval", report)
        self.assertNotIn("±", report)
        self.assertTrue(all((output / filename).stat().st_size > 1000 for filename in ("rates_1.png", "rates_2.png")))
        self.assertEqual(json.loads((output / "metadata.json").read_text())["status"], "complete")

    def test_unavailable_is_distinct_from_not_reached_and_zero(self):
        output = self.report([self.make_run(methods=["rbf"], attacks=2)])
        rows = read_csv(output / "minimum_windows.csv")
        self.assertEqual(next(r for r in rows if r["split"] == "attacker")["status"], "unavailable")
        self.assertEqual(next(r for r in rows if r["split"] == "mixed_0.25")["status"], "reached")
        self.assertIn("test_attack: 2 < 4", (output / "REPORT.md").read_text(encoding="utf-8"))
        no_attacks = self.report([self.make_run(dataset="no_attacks", methods=["rbf"], attacks=0)], "no_attack_report")
        self.assertTrue(all(r["status"] == "unavailable" for r in read_csv(no_attacks / "minimum_windows.csv")))
        partial = self.report([self.make_run(dataset="partial", methods=["rbf"], attacks=1)], "partial_report")
        mixed = next(r for r in read_csv(partial / "minimum_windows.csv") if r["split"] == "mixed_0.25")
        self.assertEqual(mixed["minimum_effective_window_size"], "4")
        self.assertTrue(any(r["window_size"] == "8" and r["split"] == "mixed_0.25" and r["supported"] == "False"
                            for r in read_csv(partial / "availability.csv")))

    def test_datasets_and_seeds_are_not_pooled(self):
        a = self.make_run(dataset="a", seeds=(1, 20), methods=["rbf"], rates={("rbf", 20, 4, "mixed_0.25"): 0})
        b = self.make_run(dataset="b", seeds=(1, 20), methods=["rbf"], rates={("rbf", 1, 4, "mixed_0.25"): 0, ("rbf", 20, 4, "mixed_0.25"): 0})
        output = self.report([a, b])
        means = {(r["dataset"], r["window_size"], r["split"]): r for r in read_csv(output / "overall.csv")}
        self.assertEqual(means[("a", "4", "mixed_0.25")]["rate_mean"], "0.45")
        self.assertEqual(means[("b", "4", "mixed_0.25")]["rate_mean"], "0.0")
        self.assertEqual(means[("a", "4", "mixed_0.25")]["seeds"], "2")
        self.assertIn("±", (output / "REPORT.md").read_text(encoding="utf-8"))
        self.assertEqual(len(read_csv(output / "minimum_windows.csv")), 8)

    def test_missing_conditions_scores_or_seeds_cannot_pass_for_all_methods(self):
        run = self.make_run()
        original_meta = json.loads((run / "metadata.json").read_text())
        original_summary = read_csv(run / "summary.csv")
        path = run / "seed_1/window_4/scores.csv"
        cal_path = run / "seed_1/window_4/calibration_scores.csv"
        original_scores, original_calibration = read_csv(path), read_csv(cal_path)
        for index, mutation in enumerate(("seed", "condition", "score", "rate", "decision", "calibration")):
            with self.subTest(mutation=mutation):
                meta = copy.deepcopy(original_meta)
                summary = copy.deepcopy(original_summary)
                scores = copy.deepcopy(original_scores)
                calibration = copy.deepcopy(original_calibration)
                if mutation == "seed":
                    meta["cases"] = []
                elif mutation == "condition":
                    summary = [r for r in summary if r["split"] != "attacker"]
                    scores = [r for r in scores if r["split"] != "attacker"]
                elif mutation == "score":
                    scores = scores[1:]
                elif mutation == "rate":
                    summary[0]["detection_rate"] = .99
                elif mutation == "decision":
                    scores[0]["suspicious"] = 0
                else:
                    calibration[0]["score"] = 10
                write_json(run / "metadata.json", meta)
                write_csv(run / "summary.csv", summary)
                write_csv(path, scores)
                write_csv(cal_path, calibration)
                with self.assertRaises(ValueError):
                    self.report([run], f"bad_{index}")
                self.assertFalse((self.root / f"bad_{index}").exists())

    def test_fpr_uses_the_same_supported_seeds_as_tpr(self):
        run = self.make_run(seeds=(1, 20), methods=["rbf"], attacks={1: 1, 20: 40},
                            rates={("rbf", 1, 8, "heldout_benign"): 0,
                                   ("rbf", 20, 8, "heldout_benign"): 2})
        output = self.report([run])
        rows = read_csv(output / "overall.csv")
        attack = next(r for r in rows if r["window_size"] == "8" and r["split"] == "mixed_0.25")
        benign = next(r for r in rows if r["window_size"] == "8" and r["split"] == "heldout_benign")
        self.assertEqual(attack["seeds"], "1")
        self.assertEqual(attack["measured_fpr_mean"], "0.1")
        self.assertEqual(benign["rate_mean"], "0.05")

    def test_incomplete_duplicate_incompatible_and_overwrite_are_rejected(self):
        run = self.make_run(methods=["rbf"])
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            self.report([run, run], "duplicate")
        meta = json.loads((run / "metadata.json").read_text())
        meta["status"] = "failed"
        write_json(run / "metadata.json", meta)
        with self.assertRaisesRegex(ValueError, "Incomplete"):
            self.report([run], "incomplete")
        meta["status"] = "complete"
        meta["lock_id"] = "different"
        write_json(run / "metadata.json", meta)
        with self.assertRaisesRegex(ValueError, "identity differs"):
            self.report([run], "incompatible")
        existing = self.root / "existing"
        existing.mkdir()
        with self.assertRaises(FileExistsError):
            self.report([run], "existing")
