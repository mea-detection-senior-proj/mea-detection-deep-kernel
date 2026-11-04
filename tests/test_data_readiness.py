"""Check audit conclusions against explicit small capacity/leakage examples."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from experiments.audit_data import capacity_rows, provenance_records, row_stats, training_rows, verify_partitions


class ReadinessTests(unittest.TestCase):
    def test_provenance_loads_without_pilot_directory(self):
        record = {"revision": "fixture", "files": [
            {"path": "data\\fixture\\normal\\queries.jsonl", "sha256": "fixture-hash"}]}
        temporary_root = Path(__file__).resolve().parents[1] / "artifacts/test_tmp"
        temporary_root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=temporary_root) as directory:
            root = Path(directory)
            path = root / "data_pipeline/provenance/ADDITIONAL_DATA_PROVENANCE.json"
            path.parent.mkdir(parents=True)
            path.write_text(json.dumps(record), encoding="utf-8")
            with patch("experiments.audit_data.ROOT", root):
                hashes, loaded = provenance_records()
            self.assertEqual(hashes, {"data/fixture/normal/queries.jsonl": "fixture-hash"})
            self.assertEqual(loaded, record)

    def test_mixed_window_can_fit_when_pure_window_cannot(self):
        sizes = {part: {"benign": 2000, "attack": 50}
                 for part in ("train", "validation", "reference", "calibration", "test")}
        rows = capacity_rows("fixture", 42, sizes)
        mixture = next(r for r in rows if r["window_size"] == 100 and r["requested_ratio"] == .25)
        pure = next(r for r in rows if r["window_size"] == 100 and r["requested_ratio"] == 1)
        self.assertTrue(mixture["supported"])
        self.assertEqual(mixture["condition_disjoint_test_windows_row_bound"], 2)
        self.assertFalse(pure["supported"])
        self.assertIn("test_attack: 50 < 100", pure["shortages"])

    def test_training_capacity_checks_validation_and_disjoint_benign_pair(self):
        sizes = {"train": {"benign": 199, "attack": 300},
                 "validation": {"benign": 199, "attack": 150}}
        rows = training_rows("fixture", 1, sizes)
        pure100 = next(r for r in rows if r["training_window_size"] == 100 and r["training_mode"] == "pure")
        pure250 = next(r for r in rows if r["training_window_size"] == 250 and r["training_mode"] == "pure")
        mixed100 = next(r for r in rows if r["training_window_size"] == 100 and r["requested_ratio"] == .01)
        self.assertTrue(pure100["supported"])
        self.assertTrue(mixed100["supported"])
        self.assertFalse(pure250["supported"])
        self.assertIn("validation_attack: 150 < 250", pure250["shortages"])

    def test_duplicate_accounting_and_independent_partition_verification(self):
        rows = [{"id": "a", "query": "Same  TEXT"}, {"id": "b", "query": "same text"}]
        self.assertEqual(row_stats(rows)["duplicate_text_rows"], 1)
        partitions = {"train": {"benign": [rows[0]], "attack": []},
                      "test": {"benign": [rows[1]], "attack": []}}
        with self.assertRaisesRegex(ValueError, "Cross-partition text collision"):
            verify_partitions(partitions, "id-text-only")


if __name__ == "__main__":
    unittest.main()
