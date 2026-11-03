"""Resolve defaults, JSON settings and explicit command-line overrides."""
import json
import math
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
DEFAULTS = {
    "dataset": None, "dataset_config": None,
    "data_root": "data", "output": "artifacts/mmd_comparison", "cache_dir": "artifacts/cache/embeddings",
    "embedding_model": "BAAI/bge-small-en-v1.5", "embedding_revision": None, "query_prefix": "",
    "device": "cpu", "dtype": "float32", "encode_batch_size": 64,
    "methods": ["rbf", "multi_rbf"], "seeds": [1, 20, 42], "window_sizes": [100, 250, 500, 1500],
    "attacker_ratios": [.01, .05, .1, .25, 1.0], "reference_repeats": 20,
    "calibration_windows": 200, "test_windows": 100, "target_fpr": .05, "bandwidth_sample_size": 2000,
    "protocol_lock": None, "training": {},
}


def project_path(value):
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def load_config(path=None, overrides=None):
    supplied = json.loads(Path(path).read_text(encoding="utf-8-sig")) if path else {}
    if not isinstance(supplied, dict) or (overrides is not None and not isinstance(overrides, dict)):
        raise ValueError("Config and overrides must be objects")
    unknown = set(supplied) - (set(DEFAULTS) | {"dataset_config"})
    if unknown:
        raise ValueError(f"Unknown config keys: {sorted(unknown)}")
    unknown_overrides = set(overrides or {}) - (set(DEFAULTS) | {"dataset_config"})
    if unknown_overrides:
        raise ValueError(f"Unknown overrides: {sorted(unknown_overrides)}")
    config = {**DEFAULTS, **supplied, **(overrides or {})}
    if "training" in (overrides or {}):
        if not isinstance(supplied.get("training", {}), dict) or not isinstance(overrides["training"], dict):
            raise ValueError("training must be an object")
        config["training"] = {**supplied.get("training", {}), **overrides["training"]}
    if "dataset" in (overrides or {}):
        config["dataset_config"] = None
    elif "dataset_config" in (overrides or {}):
        config["dataset"] = None
    name = config.get("dataset")
    if name is not None:
        if not isinstance(name, str) or not name.strip() or Path(name).name != name or name in (".", "..") or any(c in name for c in "/\\:"):
            raise ValueError("dataset must be one folder name under data_root")
        if config.get("dataset_config") is not None:
            raise ValueError("Select dataset or legacy dataset_config, not both")
    elif not isinstance(config.get("dataset_config"), str) or not config["dataset_config"].strip():
        raise ValueError("dataset is required: select a folder under data_root")
    for key in ("data_root", "output", "cache_dir", "embedding_model", "device"):
        if not isinstance(config[key], str) or not config[key].strip():
            raise ValueError(f"{key} must be a nonempty string")
    for key in ("reference_repeats", "calibration_windows", "test_windows", "encode_batch_size", "bandwidth_sample_size"):
        if type(config[key]) is not int or config[key] < (2 if key == "bandwidth_sample_size" else 1):
            raise ValueError(f"Invalid positive count: {key}")
    for key, minimum in (("seeds", 0), ("window_sizes", 2)):
        values = config[key]
        if not isinstance(values, list) or not values or any(type(v) is not int or v < minimum for v in values):
            raise ValueError(f"Invalid {key}")
        if len(set(values)) != len(values):
            raise ValueError(f"Duplicate {key}")
    methods = config["methods"]
    if not isinstance(methods, list) or not methods or any(m not in ("rbf", "multi_rbf", "deep_kernel") for m in methods) or len(set(methods)) != len(methods):
        raise ValueError("methods must contain distinct rbf/multi_rbf/deep_kernel entries")
    if config["protocol_lock"] is not None and (not isinstance(config["protocol_lock"], str) or not config["protocol_lock"].strip()):
        raise ValueError("protocol_lock must be a nonempty path string")
    from detectors.deep_kernel_mmd.training import validate_training
    config["training"] = validate_training(config["training"])
    ratios = config["attacker_ratios"]
    if not isinstance(ratios, list) or not ratios or any(type(r) not in (int, float) or not math.isfinite(r) or not 0 < r <= 1 for r in ratios):
        raise ValueError("attacker_ratios must be positive fractions <= 1")
    if len(set(ratios)) != len(ratios):
        raise ValueError("Duplicate attacker_ratios")
    if type(config["target_fpr"]) not in (int, float) or not 0 < config["target_fpr"] < 1:
        raise ValueError("target_fpr must be between zero and one")
    if config["dtype"] not in ("float32", "float64") or not isinstance(config["query_prefix"], str):
        raise ValueError("Invalid dtype/query_prefix")
    model_path = project_path(config["embedding_model"])
    if model_path.is_dir():
        config["embedding_model"] = str(model_path.resolve())
    elif not isinstance(config["embedding_revision"], str) or not re.fullmatch(r"[0-9a-fA-F]{40}", config["embedding_revision"]):
        raise ValueError("Remote encoders require a pinned 40-character embedding_revision; alternatively supply a local encoder folder")
    return config


