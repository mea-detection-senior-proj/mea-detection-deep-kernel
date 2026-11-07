"""Bounded offline verification; mock collection plus existing numeric regressions."""
import argparse
from collections import Counter
import hashlib
import io
import json
import os
from pathlib import Path
import platform
import sqlite3
import subprocess
import sys
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
HERE = ROOT / "stream_prada_order"


def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path, value):
    path.write_bytes((json.dumps(value, indent=2, ensure_ascii=True, allow_nan=False) + "\n").encode())


def worker():
    import socket
    def disabled(*_, **__): raise RuntimeError("network_disabled_for_offline_tests")
    socket.socket.connect = disabled
    socket.socket.connect_ex = disabled
    socket.create_connection = disabled
    started = time.perf_counter()
    suite = unittest.defaultTestLoader.discover(str(HERE / "tests"))
    def ids(node):
        for item in node:
            if isinstance(item, unittest.TestSuite): yield from ids(item)
            else: yield item.id()
    test_ids = list(ids(suite))
    output = io.StringIO()
    result = unittest.TextTestRunner(stream=output, verbosity=2).run(suite)
    try:
        import psutil
        peak = psutil.Process().memory_info().peak_wset
    except (ImportError, AttributeError):
        peak = None
    record = {"status": "passed" if result.wasSuccessful() else "failed",
              "tests_run": result.testsRun, "failures": len(result.failures), "errors": len(result.errors),
              "skipped": len(result.skipped), "seconds": time.perf_counter() - started,
              "test_ids": test_ids, "tests_by_module": dict(Counter(t.split(".")[0] for t in test_ids)),
              "process_peak_working_set_bytes": peak, "network_connect_guard": True,
              "cuda_visible_devices": os.environ.get("CUDA_VISIBLE_DEVICES"),
              "fixture_scope": "New collector tests use mock numeric traffic only; old regressions use numeric CPU matrices.",
              "failed_test_ids": [t.id() for t, _ in result.failures + result.errors]}
    print(json.dumps(record, ensure_ascii=True))
    if not result.wasSuccessful(): print(output.getvalue(), file=sys.stderr)
    return 0 if result.wasSuccessful() else 1


def verify(output):
    require = lambda condition: None if condition else (_ for _ in ()).throw(ValueError("verification_gate_failed"))
    require(not output.exists())
    require(subprocess.check_output(["git", "branch", "--show-current"], cwd=ROOT, text=True).strip() == "experiment/stream-prada-order")
    require(not subprocess.check_output(["git", "diff", "--name-only"], cwd=ROOT, text=True).strip())
    tracked = subprocess.check_output(["git", "ls-files"], cwd=ROOT, text=True).splitlines()
    baseline = {p: sha(ROOT / p) for p in tracked if (ROOT / p).is_file()}
    paths = [Path(__file__), *sorted((HERE / "traffic_collection").rglob("*.py")),
             *sorted((HERE / "traffic_collection").rglob("*.json")),
             *sorted((HERE / "tests").glob("*phase_g*.py")), HERE / "traffic_local/.gitignore"]
    sources = {p.relative_to(ROOT).as_posix(): sha(p) for p in paths}
    output.mkdir(parents=True)
    preflight = {"gate_seconds": 120, "cpu_only": True, "full_regression_memory_review_limit_bytes": 2 * 1024**3,
                 "python": platform.python_version(), "sqlite": sqlite3.sqlite_version,
                 "head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
                 "main_sha": subprocess.check_output(["git", "rev-parse", "main"], cwd=ROOT, text=True).strip(),
                 "frozen_sources": sources}
    write(output / "preflight.json", preflight)
    env = dict(os.environ, CUDA_VISIBLE_DEVICES="", HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1", PYTHONIOENCODING="utf-8")
    try:
        child = subprocess.run([sys.executable, str(Path(__file__).resolve()), "--worker"], cwd=ROOT,
                               env=env, capture_output=True, text=True, encoding="utf-8", timeout=120)
        result = json.loads(child.stdout)
        write(output / "test_results.json", result)
        require(child.returncode == 0 and result["status"] == "passed")
        require(result["process_peak_working_set_bytes"] is None or result["process_peak_working_set_bytes"] <= 2 * 1024**3)
    except subprocess.TimeoutExpired:
        write(output / "test_results.json", {"status": "blocked_timeout", "gate_seconds": 120})
        raise
    sys.path.insert(0, str(HERE))
    from traffic_collection.adapters import QwenLocalAdapter
    from traffic_collection.schema import strict_json, validate_manifest
    validate_manifest(strict_json((HERE / "traffic_collection/fixtures/mock_manifest_v1.json").read_bytes()))
    write(output / "qwen_disabled_plan.json", QwenLocalAdapter().deployment_plan())
    summary = {"status": "passed", "tests_run": result["tests_run"],
               "new_phase_g_tests": sum(n for name, n in result["tests_by_module"].items() if name.startswith("test_phase_g")),
               "legacy_numeric_regression_tests": sum(n for name, n in result["tests_by_module"].items() if not name.startswith("test_phase_g")),
               "runtime_seconds": result["seconds"], "real_victim_requests": 0,
               "model_weight_downloads": 0, "model_weights_loaded": 0, "extraction_runs": 0, "student_training_runs": 0,
               "private_participant_traffic_collected": 0, "real_horizon256_feasibility": "unmeasured_no_authorized_native_traffic",
               "scientifically_verified_new_independent_sessions": None,
               "prior_tracked_files_unchanged": all(sha(ROOT / p) == h for p, h in baseline.items()),
               "frozen_sources_unchanged": all(sha(ROOT / p) == h for p, h in sources.items()),
               "main_unchanged": subprocess.check_output(["git", "rev-parse", "main"], cwd=ROOT, text=True).strip() == preflight["main_sha"],
               "pushed": False}
    write(output / "verification.json", summary)
    write(output / "artifact_hashes.json", {p.name: sha(p) for p in sorted(output.iterdir()) if p.is_file() and p.name != "artifact_hashes.json"})
    require(summary["prior_tracked_files_unchanged"] and summary["frozen_sources_unchanged"] and summary["main_unchanged"])
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--worker", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.worker: raise SystemExit(worker())
    if not args.output: parser.error("--output is required")
    verify(args.output)
