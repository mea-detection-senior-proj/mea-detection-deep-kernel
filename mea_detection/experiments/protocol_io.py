"""Protocol persistence, draw serialization and integrity verification."""
import hashlib
import json
from pathlib import Path

import numpy as np

from mea_detection.data.datasets import digest
from mea_detection.data.windows import Window
from mea_detection.identity import code_identity
from .protocol import validate_settings


def sha256(path):
    result = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest()


def save_draws(path, calibration, test):
    arrays = {}
    for phase, windows in (("calibration", calibration), ("test", test)):
        arrays[f"{phase}_indices"] = np.stack([w.indices for w in windows]).astype(np.int32)
        arrays[f"{phase}_references"] = np.stack([w.references for w in windows]).astype(np.int32)
        arrays[f"{phase}_counts"] = np.array([w.attacker_count for w in windows], dtype=np.int32)
        arrays[f"{phase}_ratios"] = np.array([w.requested_ratio for w in windows])
        arrays[f"{phase}_splits"] = np.array([w.split for w in windows])
    np.savez_compressed(path, **arrays)


def load_draws(path):
    with np.load(path, allow_pickle=False) as arrays:
        return tuple([Window(str(split), indices, references, int(count), float(ratio))
                      for split, indices, references, count, ratio in zip(
                          arrays[f"{phase}_splits"], arrays[f"{phase}_indices"], arrays[f"{phase}_references"],
                          arrays[f"{phase}_counts"], arrays[f"{phase}_ratios"])]
                     for phase in ("calibration", "test"))


def verify_lock(path, config, *, require_current_source=True):
    metadata = json.loads((path / "lock.json").read_text(encoding="utf-8"))
    if metadata.get("status") != "complete":
        raise ValueError("Protocol lock is incomplete")
    lock_id = metadata.pop("lock_id")
    if digest(json.dumps(metadata, sort_keys=True)) != lock_id:
        raise ValueError("Protocol lock metadata was modified")
    metadata["lock_id"] = lock_id
    validate_settings(metadata, config)
    if require_current_source and metadata.get("code", {}).get("pipeline_source_sha256") != code_identity()["pipeline_source_sha256"]:
        raise ValueError("Protocol source identity is incompatible; prepare a new protocol lock")
    for relative, expected in metadata["files"].items():
        candidate = path / relative
        if not candidate.resolve().is_relative_to(path.resolve()) or sha256(candidate) != expected:
            raise ValueError(f"Locked artifact modified: {relative}")
    return metadata


