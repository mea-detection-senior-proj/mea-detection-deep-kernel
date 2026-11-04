"""Focused dependency boundaries and archive provenance checks."""
import ast
import hashlib
import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class ArchitectureTests(unittest.TestCase):
    def test_dependency_boundaries_and_cycles(self):
        package = ROOT / "mea_detection"
        modules = {}
        for path in package.rglob("*.py"):
            parts = list(path.relative_to(ROOT).with_suffix("").parts)
            if parts[-1] == "__init__":
                parts.pop()
            modules[".".join(parts)] = path
        graph = {}
        numerical = {"data.datasets", "data.windows", "data.capacity", "data.audit",
                     "detection.mmd", "detection.training", "detection.settings",
                     "detection.kernels.fixed", "detection.kernels.deep",
                     "evaluation.windows", "evaluation.comparison"}
        for module, path in modules.items():
            imports = set()
            parent = module if path.name == "__init__.py" else module.rpartition(".")[0]
            for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
                if isinstance(node, ast.Import):
                    imports.update(alias.name for alias in node.names)
                elif isinstance(node, ast.ImportFrom):
                    target = "." * node.level + (node.module or "")
                    imports.add(importlib.util.resolve_name(target, parent) if node.level else target)
            for target in imports:
                self.assertFalse(target.startswith(("pilot", "MMD_detection", "old-detectors",
                                                    "detectors", "data_pipeline", "experiments")), (module, target))
                if not module.startswith("mea_detection.cli") and module != "mea_detection.__main__":
                    self.assertFalse(target.startswith("mea_detection.cli"), (module, target))
                if module.startswith("mea_detection.data"):
                    self.assertFalse(target.startswith(("mea_detection.detection", "mea_detection.experiments")), (module, target))
                if module.startswith("mea_detection.embeddings"):
                    self.assertFalse(target.startswith(("mea_detection.detection", "mea_detection.experiments",
                                                        "mea_detection.reporting")), (module, target))
                if module.removeprefix("mea_detection.") in numerical:
                    self.assertFalse(target in {"pathlib", "json", "csv", "os", "subprocess", "argparse"}, (module, target))
                    self.assertFalse(target.startswith(("mea_detection.experiments", "mea_detection.reporting",
                                                        "mea_detection.embeddings", "mea_detection.runtime",
                                                        "mea_detection.detection.checkpoints", "mea_detection.data.io")), (module, target))
                if module.startswith("mea_detection.reporting"):
                    self.assertFalse(target.startswith(("mea_detection.detection", "mea_detection.embeddings",
                                                        "mea_detection.experiments.locked", "mea_detection.experiments.workflow")), (module, target))
            graph[module] = imports & modules.keys()
        complete = set()

        def visit(module, chain):
            self.assertNotIn(module, chain, " -> ".join([*chain, module]))
            if module in complete:
                return
            for dependency in graph[module]:
                visit(dependency, [*chain, module])
            complete.add(module)

        for module in graph:
            visit(module, [])

    def test_archived_python_sources_match_inventory(self):
        manifest = json.loads((ROOT / "old-detectors/manifest.json").read_text(encoding="utf-8"))
        for entry in manifest["files"]:
            if entry["original"].endswith(".py"):
                path = ROOT / entry["archived"]
                self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), entry["sha256"], str(path))
                self.assertFalse((ROOT / entry["original"]).exists(), entry["original"])
