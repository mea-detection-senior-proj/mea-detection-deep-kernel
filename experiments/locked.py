"""Materialize and verify an immutable shared evaluation plan before training."""
import hashlib
import json
import os
from pathlib import Path
import time

import numpy as np
import torch

from data_pipeline.datasets import digest, load_dataset, split_rows
from data_pipeline.embeddings import embed_texts
from data_pipeline.windows import Window, make_windows
from detectors.mmd.detector import MMDDetector, median_bandwidth
from detectors.deep_kernel_mmd.model import DeepKernelMMD
from detectors.deep_kernel_mmd.training import fit_kernel
from evaluation.windows import evaluate
from experiments.configuration import ROOT, project_path
from experiments.artifacts import code_identity, write_csv, write_json

LOCK_KEYS = ("data_root", "embedding_model", "embedding_revision", "query_prefix", "dtype",
             "seeds", "window_sizes", "attacker_ratios", "reference_repeats", "calibration_windows",
             "test_windows", "target_fpr", "bandwidth_sample_size")


def protocol_settings(config):
    selector = {"dataset": config["dataset"]} if config.get("dataset") else {"dataset_config": config["dataset_config"]}
    return {**selector, **{key: config[key] for key in LOCK_KEYS}}


def runtime():
    os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")
    torch.use_deterministic_algorithms(True)
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False


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


def prepare(config, output):
    runtime()
    output = project_path(str(output))
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite protocol lock: {output}")
    spec, benign, attack = load_dataset(config, ROOT)
    rows = {"benign": benign, "attack": attack}
    plans = [(seed, *split_rows(rows["benign"], rows["attack"], seed, spec["grouping_policy"])) for seed in config["seeds"]]
    texts = sorted({r["query"] for _, parts, _, _ in plans for classes in parts.values()
                    for entries in classes.values() for r in entries})
    positions = {text: i for i, text in enumerate(texts)}
    output.mkdir(parents=True, exist_ok=False)
    metadata = {"status": "preparing", "protocol": "locked-fixed-window-v1",
                "settings": protocol_settings(config), "dataset": spec,
                "data_sha256": {label: digest(json.dumps(entries, sort_keys=True, ensure_ascii=False)) for label, entries in rows.items()},
                "code": code_identity(), "files": {}, "cases": [], "seeds": {}}
    write_json(output / "lock.json", metadata)
    try:
        encoded, encoder = embed_texts(texts, config["embedding_model"], config["embedding_revision"], config["query_prefix"],
                                     config["encode_batch_size"], config["device"], project_path(config["cache_dir"]))
        np.save(output / "embeddings.npy", encoded)
        write_json(output / "embedding_manifest.json", [digest(text) for text in texts])
        z = torch.as_tensor(encoded, dtype=getattr(torch, config["dtype"]), device=config["device"])
        for seed, partitions, audit, manifest in plans:
            pools = {p: {label: [positions[r["query"]] for r in entries] for label, entries in classes.items()}
                     for p, classes in partitions.items()}
            ref = torch.as_tensor(pools["reference"]["benign"], device=z.device)
            sigma = median_bandwidth(z[ref], config["bandwidth_sample_size"], np.random.default_rng(np.random.SeedSequence([seed, 0])))
            directory = output / f"seed_{seed}"
            directory.mkdir()
            write_json(directory / "pools.json", pools)
            write_json(directory / "split_manifest.json", manifest)
            write_json(directory / "split_audit.json", audit)
            metadata["seeds"][str(seed)] = {"median_bandwidth": sigma, "sizes": audit["sizes"]}
            for size in config["window_sizes"]:
                print(f"Locking seed {seed}, window {size}", flush=True)
                cal_rng, test_rng = [np.random.default_rng(s) for s in np.random.SeedSequence([seed, size, 1]).spawn(2)]
                calibration = make_windows(pools["calibration"]["benign"], [], pools["reference"]["benign"], size,
                                           config["reference_repeats"], config["calibration_windows"], [0], cal_rng)
                test = make_windows(pools["test"]["benign"], pools["test"]["attack"], pools["reference"]["benign"], size,
                                    config["reference_repeats"], config["test_windows"], [0] + config["attacker_ratios"], test_rng)
                relative = f"seed_{seed}/window_{size}.npz"
                save_draws(output / relative, calibration, test)
                metadata["cases"].append({"seed": seed, "window_size": size, "draws": relative})
        metadata["files"] = {p.relative_to(output).as_posix(): sha256(p) for p in output.rglob("*") if p.is_file() and p.name != "lock.json"}
        metadata.update(status="complete", encoder=encoder)
        # This fingerprint is recorded by each consumer and checked on every load.
        metadata["lock_id"] = digest(json.dumps(metadata, sort_keys=True))
        write_json(output / "lock.json", metadata)
    except Exception as exc:
        metadata.update(status="failed", error=str(exc))
        write_json(output / "lock.json", metadata)
        raise
    print(f"Protocol locked: {output}", flush=True)
    return output


def verify_lock(path, config):
    metadata = json.loads((path / "lock.json").read_text(encoding="utf-8"))
    if metadata.get("status") != "complete":
        raise ValueError("Protocol lock is incomplete")
    lock_id = metadata.pop("lock_id")
    if digest(json.dumps(metadata, sort_keys=True)) != lock_id:
        raise ValueError("Protocol lock metadata was modified")
    metadata["lock_id"] = lock_id
    requested = protocol_settings(config)
    # Old locks retain their embedded dataset snapshot; no old JSON file is needed.
    if config.get("dataset") and "dataset_config" in metadata["settings"] and config["dataset"] == metadata["dataset"]["name"]:
        requested.pop("dataset")
        requested["dataset_config"] = metadata["settings"]["dataset_config"]
    keys = set(requested) | set(metadata["settings"])
    differences = [f"{key}: requested={requested.get(key)!r}, locked={metadata['settings'].get(key)!r}"
                   for key in sorted(keys) if requested.get(key) != metadata["settings"].get(key)]
    if differences:
        raise ValueError("Experiment settings differ from the locked evaluation protocol:\n" + "\n".join(differences)
                         + "\nUse a new protocol lock for these settings.")
    for relative, expected in metadata["files"].items():
        candidate = path / relative
        if not candidate.resolve().is_relative_to(path.resolve()) or sha256(candidate) != expected:
            raise ValueError(f"Locked artifact modified: {relative}")
    return metadata


def run_locked(config):
    runtime()
    output, lock_path = project_path(config["output"]), project_path(config["protocol_lock"])
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite run: {output}")
    lock = verify_lock(lock_path, config)
    # Training capacity is checked before creating run artifacts.
    if "deep_kernel" in config["methods"]:
        size = config["training"]["window_size"]
        for entry in lock["seeds"].values():
            for part in ("train", "validation"):
                if min(entry["sizes"][part].values()) < size:
                    raise ValueError(f"Insufficient {part} data for pure training size {size}")
    z = torch.as_tensor(np.load(lock_path / "embeddings.npy", allow_pickle=False),
                        dtype=getattr(torch, config["dtype"]), device=config["device"])
    output.mkdir(parents=True, exist_ok=False)
    write_json(output / "config.json", config)
    metadata = {"status": "running", "protocol": lock["protocol"], "protocol_lock": str(lock_path),
                "lock_id": lock["lock_id"], "code": code_identity(), "dataset": lock["dataset"],
                "software": {"torch": torch.__version__, "numpy": np.__version__, "cuda": torch.version.cuda},
                "deterministic_algorithms": True, "tf32": False, "seeds": {}, "cases": []}
    write_json(output / "metadata.json", metadata)
    summaries, started = [], time.perf_counter()
    try:
        for seed in config["seeds"]:
            sigma = lock["seeds"][str(seed)]["median_bandwidth"]
            available = {"rbf": MMDDetector((sigma,)), "multi_rbf": MMDDetector(tuple(sigma * s for s in (.5, 1, 2, 4)))}
            seed_dir = output / f"seed_{seed}"
            seed_dir.mkdir()
            pools = json.loads((lock_path / f"seed_{seed}/pools.json").read_text())
            if "deep_kernel" in config["methods"]:
                print(f"Training pure Deep Kernel: seed {seed}", flush=True)
                torch.manual_seed(seed)
                model = DeepKernelMMD(z.shape[1], sigma, config["training"]["hidden_dim"], config["training"]["feature_dim"]).to(z)
                training_started = time.perf_counter()
                def pool(part, label):
                    return z[torch.as_tensor(pools[part][label], device=z.device)]
                training = fit_kernel(model, pool("train", "benign"), pool("train", "attack"),
                                      pool("validation", "benign"), pool("validation", "attack"), config["training"], seed)
                training["elapsed_seconds"] = time.perf_counter() - training_started
                torch.save({"state_dict": model.state_dict(), "input_dim": z.shape[1], "config": config["training"],
                            "initial_base_bandwidth": sigma, "lock_id": lock["lock_id"]}, seed_dir / "deep_kernel.pt")
                write_json(seed_dir / "training.json", training)
                write_csv(seed_dir / "training_history.csv", training["history"])
                available["deep_kernel"] = model
                metadata["seeds"][str(seed)] = {"best_epoch": training["best_epoch"], "kernel_parameters": training["kernel_parameters"]}
            methods = {name: available[name] for name in config["methods"]}
            for case in (c for c in lock["cases"] if c["seed"] == seed):
                size, tick = case["window_size"], time.perf_counter()
                calibration, test = load_draws(lock_path / case["draws"])
                print(f"Evaluating {list(methods)}: seed {seed}, window {size}", flush=True)
                scores, cal_scores, summary, thresholds = evaluate(methods, z, calibration, test, config["target_fpr"])
                destination = seed_dir / f"window_{size}"
                destination.mkdir()
                write_csv(destination / "scores.csv", scores)
                write_csv(destination / "calibration_scores.csv", cal_scores)
                write_json(destination / "metadata.json", {"thresholds": thresholds, "locked_draws": case["draws"],
                           "draws_sha256": lock["files"][case["draws"]], "elapsed_seconds": time.perf_counter() - tick})
                summaries.extend({"dataset": lock["dataset"]["name"], "seed": seed, "window_size": size, **row} for row in summary)
                metadata["cases"].append({"seed": seed, "window_size": size, "draws_sha256": lock["files"][case["draws"]]})
                write_csv(output / "summary.csv", summaries)
                write_json(output / "metadata.json", metadata)
        metadata.update(status="complete", elapsed_seconds=time.perf_counter() - started)
        write_json(output / "metadata.json", metadata)
    except Exception as exc:
        metadata.update(status="failed", error=str(exc))
        write_json(output / "metadata.json", metadata)
        raise
    print(f"Complete: {output}", flush=True)
    return output
