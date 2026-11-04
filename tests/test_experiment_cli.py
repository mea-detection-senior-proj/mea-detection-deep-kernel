"""CLI precedence, no-side-effect dry runs and complete selected-method workflows."""
import contextlib
import io
import json
from pathlib import Path
import tempfile
import shutil
import unittest
from unittest.mock import patch

import numpy as np

from mea_detection.cli.run import parse_config
from mea_detection.configuration import load_config
from mea_detection.experiments.workflow import execute, preflight
from mea_detection.cli.main import main


class ExperimentCLITests(unittest.TestCase):
    def setUp(self):
        temporary_root = Path(__file__).resolve().parents[1] / "artifacts" / "test_tmp"
        temporary_root.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=temporary_root)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.dataset = self.root / "fixture"
        for label in ("benign", "attack"):
            rows = [{"id": f"{label}-{i}", "query": f"{label} text {i}"} for i in range(150)]
            directory = self.dataset / ("normal" if label == "benign" else "attacker")
            directory.mkdir(parents=True)
            (directory / "queries.jsonl").write_text("\n".join(json.dumps(row) for row in rows))
        self.settings = {"dataset": "fixture", "data_root": str(self.root),
                         "embedding_model": str(self.root), "output": str(self.root / "run"), "device": "cpu", "dtype": "float64",
                         "cache_dir": str(self.root / "cache"), "methods": ["rbf", "multi_rbf", "deep_kernel"],
                         "seeds": [42], "window_sizes": [4], "attacker_ratios": [.02, 1.], "reference_repeats": 2,
                         "calibration_windows": 4, "test_windows": 2,
                         "training": {"window_size": 4, "epochs": 1, "steps_per_epoch": 1,
                                      "validation_pairs": 2, "hidden_dim": 4, "feature_dim": 2}}
        self.path = self.root / "config.json"
        self.path.write_text(json.dumps(self.settings))

    def parse(self, *extra):
        return parse_config(["--config", str(self.path), *extra])[1:]

    def test_flags_override_only_supplied_values_and_merge_training(self):
        config, dry = self.parse("--window", "250", "--seed", "20", "--epochs", "3", "--test-windows", "500")
        self.assertEqual(config["window_sizes"], [250])
        self.assertEqual(config["seeds"], [20])
        self.assertEqual(config["test_windows"], 500)
        self.assertEqual(config["reference_repeats"], 2)
        self.assertEqual(config["training"]["epochs"], 3)
        self.assertEqual(config["training"]["window_size"], 4)
        self.assertEqual(config["training"]["hidden_dim"], 4)
        self.assertFalse(dry)
        self.assertEqual(json.loads(self.path.read_text()), self.settings)
        multiple, _ = self.parse("--window-sizes", "4", "8", "--seeds", "1", "20", "42")
        self.assertEqual(multiple["window_sizes"], [4, 8])
        self.assertEqual(multiple["seeds"], [1, 20, 42])

    def test_dataset_flags_and_config_optional(self):
        _, config, _ = parse_config(["--dataset", "Meaeq_SST-2", "--embedding-model", str(self.root),
                                     "--window", "100", "--seed", "42"])
        self.assertEqual(config["dataset"], "Meaeq_SST-2")
        self.assertIsNone(config["dataset_config"])
        self.assertEqual(config["training"]["epochs"], 30)

    def test_copied_dataset_needs_no_registry_or_json(self):
        shutil.copytree(self.dataset, self.root / "fixture v2")
        config, _ = self.parse("--dataset", "fixture v2", "--methods", "rbf")
        self.assertEqual(preflight(config)["dataset"], "fixture v2")
        self.assertEqual(preflight(config)["split_sizes"], preflight(load_config(self.path))["split_sizes"])
        (self.root / "fixture v2/attacker/queries.jsonl").unlink()
        with self.assertRaisesRegex(FileNotFoundError, "attacker"):
            preflight(config)

    def test_conflicting_flags_and_invalid_values_are_rejected(self):
        invalid = [("--window", "4", "--window-sizes", "4", "8"), ("--seed", "1", "--seeds", "42"),
                   ("--dataset", "../bad"), ("--reference-repeats", "0"), ("--attacker-ratios", "5"),
                   ("--window-sizes", "4", "4")]
        for flags in invalid:
            with self.subTest(flags=flags), contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                self.parse(*flags)

    def test_dry_run_checks_capacity_without_encoder_gpu_or_writes(self):
        config, dry = self.parse("--device", "cuda", "--dry-run")
        before = set(self.root.rglob("*"))
        with patch("mea_detection.experiments.locked.embed_texts", side_effect=AssertionError("Encoder must not load")), \
             patch("torch.cuda._lazy_init", side_effect=AssertionError("GPU must not initialize")), \
             contextlib.redirect_stdout(io.StringIO()):
            plan = execute(config, dry_run=dry)
        self.assertEqual(plan["capacity_check"], "passed; repeated windows may reuse queries")
        self.assertEqual(plan["method_cases"], 3)
        self.assertEqual(set(self.root.rglob("*")), before)
        bad = {**config, "window_sizes": [10000]}
        with self.assertRaisesRegex(ValueError, "evaluation window"):
            preflight(bad)
        self.assertFalse(Path(config["output"]).exists())

    def test_all_methods_then_baseline_only_reuse_and_lock_conflict(self):
        config = load_config(self.path)
        def fake_encoder(texts, *args):
            return np.random.default_rng(123).normal(size=(len(texts), 3)).astype(np.float32), {"fixture": True}
        with patch("mea_detection.experiments.locked.embed_texts", side_effect=fake_encoder), contextlib.redirect_stdout(io.StringIO()):
            output = execute(config)
        self.assertEqual(json.loads((output / "run.json").read_text())["status"], "complete")
        self.assertTrue((output / "results/seed_42/deep_kernel.pt").is_file())
        report = (output / "report/REPORT.md").read_text()
        self.assertIn("deep_kernel", report)
        self.assertIn("TPR 2%", report)
        self.assertNotIn("±", report)
        with self.assertRaises(FileExistsError):
            execute(config)
        baseline = {**config, "output": str(self.root / "baseline"), "methods": ["rbf"],
                    "protocol_lock": str(output / "protocol"), "training": {**config["training"], "window_size": 999}}
        with patch("mea_detection.experiments.locked.fit_detector", side_effect=AssertionError("Baseline must not train")), \
             patch("mea_detection.experiments.locked.embed_texts", side_effect=AssertionError("Reuse must not encode")), \
             contextlib.redirect_stdout(io.StringIO()):
            selected = execute(baseline)
        self.assertFalse((selected / "protocol").exists())
        report = (selected / "report/REPORT.md").read_text()
        self.assertNotIn("deep_kernel", report)
        self.assertNotIn("multi_rbf", report)
        self.assertFalse((selected / "report/paired_differences.csv").exists())
        with self.assertRaisesRegex(ValueError, "reference_repeats"):
            execute({**baseline, "output": str(self.root / "conflict"), "reference_repeats": 3})
        self.assertFalse((self.root / "conflict").exists())

    def test_failure_records_status_without_overwriting_results(self):
        config = load_config(self.path)
        with patch("mea_detection.experiments.locked.embed_texts", side_effect=RuntimeError("Encoder unavailable")), \
             contextlib.redirect_stdout(io.StringIO()), self.assertRaisesRegex(RuntimeError, "Encoder unavailable"):
            execute(config)
        status = json.loads((self.root / "run/run.json").read_text())
        self.assertEqual(status["status"], "failed")
        self.assertEqual(status["phase"], "preparing")
        self.assertFalse((self.root / "run/results").exists())

    def test_public_operations_share_preparation_and_saved_evidence(self):
        from migration_fixture import fixture_encoder
        common = ["--config", str(self.path)]
        with contextlib.redirect_stdout(io.StringIO()), \
             patch("torch.cuda._lazy_init", side_effect=AssertionError("No GPU")), \
             patch("mea_detection.experiments.locked.embed_texts", side_effect=AssertionError("No encoder")):
            before = set(self.root.rglob("*"))
            main(["run", *common, "--dry-run", "--device", "cuda"])
            self.assertEqual(set(self.root.rglob("*")), before)
            main(["audit", "--data-root", str(self.root), "--output", str(self.root / "audit")])
            self.assertTrue((self.root / "audit/audit.json").is_file())
        with contextlib.redirect_stdout(io.StringIO()), \
             patch("mea_detection.experiments.locked.embed_texts", side_effect=fixture_encoder):
            main(["prepare", *common, "--output", str(self.root / "protocol")])
        with contextlib.redirect_stdout(io.StringIO()), \
             patch("mea_detection.experiments.locked.embed_texts", side_effect=AssertionError("Reuse must not encode")):
            output = main(["run", *common, "--protocol-lock", str(self.root / "protocol")])
            main(["report", "--runs", str(output / "results"), "--output", str(self.root / "report")])
        self.assertFalse((output / "protocol").exists())
        self.assertEqual((output / "report/REPORT.md").read_bytes(), (self.root / "report/REPORT.md").read_bytes())


if __name__ == "__main__":
    unittest.main()
