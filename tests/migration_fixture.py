"""Deterministic three-method fixture captured before the package migration."""
import csv
import json
from pathlib import Path

import numpy as np


def fixture_encoder(texts, *args):
    return np.random.default_rng(123).normal(size=(len(texts), 3)).astype(np.float32), {"fixture": True}


def fixture_config(root):
    for label in ("benign", "attack"):
        directory = root / "fixture" / ("normal" if label == "benign" else "attacker")
        directory.mkdir(parents=True)
        rows = [{"id": f"{label}-{i}", "query": f"{label} text {i}"} for i in range(150)]
        (directory / "queries.jsonl").write_text("\n".join(json.dumps(r) for r in rows), encoding="utf-8")
    return {"dataset": "fixture", "data_root": str(root), "embedding_model": str(root),
            "output": str(root / "run"), "device": "cpu", "dtype": "float64",
            "cache_dir": str(root / "cache"), "methods": ["rbf", "multi_rbf", "deep_kernel"],
            "seeds": [42], "window_sizes": [4], "attacker_ratios": [.02, 1.],
            "reference_repeats": 2, "calibration_windows": 4, "test_windows": 2,
            "training": {"window_size": 4, "epochs": 1, "steps_per_epoch": 1,
                         "validation_pairs": 2, "hidden_dim": 4, "feature_dim": 2}}


def scientific_records(output):
    records = {}
    for relative in ("results/summary.csv", "results/seed_42/window_4/scores.csv",
                     "results/seed_42/window_4/calibration_scores.csv", "report/per_seed.csv",
                     "report/overall.csv", "report/minimum_windows.csv"):
        with (output / relative).open(encoding="utf-8", newline="") as stream:
            records[relative] = list(csv.DictReader(stream))
    for relative in ("protocol/seed_42/pools.json", "protocol/seed_42/split_manifest.json"):
        records[relative] = json.loads((output / relative).read_text(encoding="utf-8"))
    training = json.loads((output / "results/seed_42/training.json").read_text(encoding="utf-8"))
    training.pop("elapsed_seconds")
    records["training"] = training
    return records
