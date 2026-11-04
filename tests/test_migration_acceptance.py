"""Migration behavior, replay, held-out independence and saved-report acceptance."""
import contextlib
import copy
import io
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
import torch

from migration_fixture import fixture_config, fixture_encoder, scientific_records
from mea_detection.configuration import load_config
from mea_detection.data.datasets import digest
from mea_detection.detection.checkpoints import load_detector
from mea_detection.experiments.artifacts import write_json
from mea_detection.experiments.locked import run_locked
from mea_detection.experiments.protocol_io import load_draws, sha256, verify_lock
from mea_detection.experiments.workflow import execute
from mea_detection.reporting.comparison import summarize


class MigrationAcceptanceTests(unittest.TestCase):
    def assert_records_equal(self, actual, expected, location="records"):
        if isinstance(expected, dict):
            self.assertEqual(actual.keys(), expected.keys(), location)
            for key in expected:
                self.assert_records_equal(actual[key], expected[key], f"{location}/{key}")
        elif isinstance(expected, list):
            self.assertEqual(len(actual), len(expected), location)
            for index, value in enumerate(expected):
                self.assert_records_equal(actual[index], value, f"{location}/{index}")
        elif isinstance(expected, float):
            np.testing.assert_allclose(actual, expected, rtol=1e-10, atol=1e-12, err_msg=location)
        elif isinstance(expected, str):
            try:
                numeric = float(expected)
            except ValueError:
                self.assertEqual(actual, expected, location)
            else:
                np.testing.assert_allclose(float(actual), numeric, rtol=1e-10, atol=1e-12, err_msg=location)
        else:
            self.assertEqual(actual, expected, location)

    def test_workflow_preserves_fixture_replay_and_heldout_independence(self):
        expected = json.loads((Path(__file__).parent / "fixtures/migration_expected.json").read_text(encoding="utf-8"))
        temporary_root = Path(__file__).resolve().parents[1] / "artifacts/test_tmp"
        temporary_root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=temporary_root) as folder, contextlib.redirect_stdout(io.StringIO()):
            root = Path(folder)
            config = load_config(overrides=fixture_config(root))
            output = execute(config, encode=fixture_encoder)
            self.assert_records_equal(scientific_records(output), expected["records"])
            checkpoint = output / "results/seed_42/deep_kernel.pt"
            lock = verify_lock(output / "protocol", config)
            replay = load_detector(checkpoint, expected_lock_id=lock["lock_id"])
            encoded = torch.as_tensor(np.load(output / "protocol/embeddings.npy"), dtype=torch.float64)
            _, windows = load_draws(output / "protocol/seed_42/window_4.npz")
            saved = scientific_records(output)["results/seed_42/window_4/scores.csv"]
            for row in (r for r in saved if r["method"] == "deep_kernel"):
                window = windows[int(row["window_id"])]
                self.assertAlmostEqual(replay.score(encoded, encoded[window.indices], torch.as_tensor(window.references)),
                                       float(row["score"]), places=12)
            with self.assertRaisesRegex(ValueError, "protocol lock"):
                load_detector(checkpoint, expected_lock_id="different-lock")
            # Regeneration uses saved evidence even if training/encoding are unavailable.
            with patch("mea_detection.experiments.locked.fit_detector", side_effect=AssertionError("No training")), \
                 patch("mea_detection.embeddings.encoder.embed_texts", side_effect=AssertionError("No encoding")):
                report = summarize([output / "results"], root / "regenerated")
            for name in ("per_seed.csv", "overall.csv", "minimum_windows.csv", "REPORT.md"):
                self.assertEqual((report / name).read_bytes(), (output / "report" / name).read_bytes())
            # Change only held-out embeddings and reseal the fixture's protocol evidence.
            changed = root / "changed_protocol"
            shutil.copytree(output / "protocol", changed)
            arrays = np.load(changed / "embeddings.npy")
            pools = json.loads((changed / "seed_42/pools.json").read_text())
            indices = pools["test"]["benign"] + pools["test"]["attack"]
            arrays[indices] += 100
            np.save(changed / "embeddings.npy", arrays)
            changed_lock = copy.deepcopy(lock)
            changed_lock["files"]["embeddings.npy"] = sha256(changed / "embeddings.npy")
            changed_lock.pop("lock_id")
            changed_lock["lock_id"] = digest(json.dumps(changed_lock, sort_keys=True))
            write_json(changed / "lock.json", changed_lock)
            second = run_locked({**config, "protocol_lock": str(changed), "output": str(root / "changed_results")})
            first_state = torch.load(checkpoint, weights_only=True)["state_dict"]
            second_state = torch.load(second / "seed_42/deep_kernel.pt", weights_only=True)["state_dict"]
            for key in first_state:
                self.assertTrue(torch.equal(first_state[key], second_state[key]), key)
            original_meta = json.loads((output / "results/seed_42/window_4/metadata.json").read_text())
            changed_meta = json.loads((second / "seed_42/window_4/metadata.json").read_text())
            self.assertEqual(original_meta["thresholds"], changed_meta["thresholds"])
            # Source tampering cannot be made executable by merely resealing a lock.
            changed_lock["code"]["pipeline_source_sha256"] = "historical-source"
            changed_lock.pop("lock_id")
            changed_lock["lock_id"] = digest(json.dumps(changed_lock, sort_keys=True))
            write_json(changed / "lock.json", changed_lock)
            with self.assertRaisesRegex(ValueError, "source identity"):
                verify_lock(changed, config)
            state = torch.load(checkpoint, weights_only=True)
            state["code"] = "historical-source"
            torch.save(state, root / "incompatible.pt")
            with self.assertRaisesRegex(ValueError, "source identity"):
                load_detector(root / "incompatible.pt")
