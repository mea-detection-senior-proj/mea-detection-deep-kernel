"""Materialize and verify an immutable shared evaluation plan before training."""
import json
import time

import numpy as np
import torch

from mea_detection.data.datasets import digest
from mea_detection.data.io import load_dataset
from mea_detection.data.capacity import require_training_capacity
from mea_detection.embeddings.encoder import embed_texts
from mea_detection.detection.mmd import MMDDetector
from mea_detection.detection.kernels.fixed import median_bandwidth
from mea_detection.detection.training import fit_detector
from mea_detection.evaluation.windows import evaluate
from mea_detection.configuration import ROOT, project_path
from mea_detection.identity import code_identity
from mea_detection.experiments.artifacts import write_csv, write_json
from mea_detection.runtime import runtime
from mea_detection.detection.checkpoints import save_detector
from .protocol import protocol_settings, partition_plans, evaluation_draws
from .protocol_io import sha256, save_draws, load_draws, verify_lock

def prepare(config, output, *, encode=None, dataset_loader=load_dataset):
    runtime()
    output = project_path(str(output))
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite protocol lock: {output}")
    spec, benign, attack = dataset_loader(config, ROOT)
    rows = {"benign": benign, "attack": attack}
    plans = partition_plans(config, spec, benign, attack)
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
        encoded, encoder = (encode or embed_texts)(texts, config["embedding_model"], config["embedding_revision"], config["query_prefix"],
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
                calibration, test = evaluation_draws(config, pools, seed, size)
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


def run_locked(config):
    runtime()
    output, lock_path = project_path(config["output"]), project_path(config["protocol_lock"])
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite run: {output}")
    lock = verify_lock(lock_path, config)
    # Training capacity is checked before creating run artifacts.
    if "deep_kernel" in config["methods"]:
        size = config["training"]["window_size"]
        for seed, entry in lock["seeds"].items():
            try:
                require_training_capacity(entry["sizes"], size)
            except ValueError as exc:
                raise ValueError(f"Seed {seed}: {exc}") from exc
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
                def pool(part, label):
                    return z[torch.as_tensor(pools[part][label], device=z.device)]
                training_started = time.perf_counter()
                model, training = fit_detector(pool("train", "benign"), pool("train", "attack"),
                                               pool("validation", "benign"), pool("validation", "attack"),
                                               sigma, config["training"], seed)
                training["elapsed_seconds"] = time.perf_counter() - training_started
                save_detector(seed_dir / "deep_kernel.pt", model, config["training"], lock["lock_id"], sigma)
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
