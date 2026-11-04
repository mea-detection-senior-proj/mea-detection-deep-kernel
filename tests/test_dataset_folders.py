"""Discover folders without dataset metadata and preserve source grouping."""
import json
from pathlib import Path
import tempfile
import unittest

from mea_detection.data.io import load_dataset
from mea_detection.data.datasets import split_rows
from mea_detection.data.readiness import verify_partitions


class DatasetFolderTests(unittest.TestCase):
    def test_context_policy_follows_content_including_partial_formats(self):
        temporary_root = Path(__file__).resolve().parents[1] / "artifacts" / "test_tmp"
        temporary_root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=temporary_root) as folder:
            root = Path(folder)
            name = "new dataset v2"
            for label in ("normal", "attacker"):
                (root / name / label).mkdir(parents=True)
            benign = [{"id": f"b{i}", "query": f"benign {i}"} for i in range(20)]
            attack = [{"id": f"a{i}", "query": f"Given this context: source {i // 2} Can you answer this question briefly: q{i}"}
                      for i in range(20)]
            def write(label, rows):
                (root / name / label / "queries.jsonl").write_text("\n".join(json.dumps(r) for r in rows))
            write("normal", benign)
            write("attacker", attack)
            config = {"dataset": name, "data_root": str(root)}
            spec, b, a = load_dataset(config, root)
            self.assertEqual(spec["grouping_policy"], "id-text-attack-context")
            reference, _, _ = split_rows(b, a, 42, "id-text-attack-context")
            observed, _, _ = split_rows(b, a, 42, spec["grouping_policy"])
            self.assertEqual(reference, observed)
            write("attacker", attack + [{"id": "unparsed", "query": "different format"}])
            spec, b, a = load_dataset(config, root)
            self.assertEqual(spec["grouping_policy"], "id-text-available-context")
            self.assertEqual(spec["recognized_attack_context_rows"], 20)
            partitions, audit, _ = split_rows(b, a, 42, spec["grouping_policy"])
            verify_partitions(partitions, spec["grouping_policy"])
            self.assertFalse(audit["source_provenance_available"])
            write("attacker", [{"id": f"a{i}", "query": f"plain attack {i}"} for i in range(20)])
            spec, _, _ = load_dataset(config, root)
            self.assertEqual(spec["grouping_policy"], "id-text-only")


if __name__ == "__main__":
    unittest.main()
