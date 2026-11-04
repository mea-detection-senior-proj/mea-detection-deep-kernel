"""Config-driven experiments; run --help for command-line overrides."""
import json
import time

import numpy as np
import torch

from data_pipeline.datasets import digest, load_dataset, split_rows
from data_pipeline.capacity import require_evaluation_capacity
from data_pipeline.embeddings import embed_texts
from data_pipeline.windows import make_windows
from detectors.mmd.detector import MMDDetector, median_bandwidth
from evaluation.windows import evaluate
from experiments.configuration import ROOT, DEFAULTS, project_path, load_config
from experiments.artifacts import write_json, write_csv, code_identity


def run(config):
    if config.get("protocol_lock"):
        from experiments.locked import run_locked
        return run_locked(config)
    if "deep_kernel" in config["methods"]:
        raise ValueError("Deep Kernel comparisons require a prepared protocol_lock")
    output = project_path(config["output"])
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite existing run: {output}")
    spec, benign, attack = load_dataset(config, ROOT)
    print(f"Dataset {spec['name']}: {len(benign)} benign / {len(attack)} attack rows", flush=True)
    plans = []
    for seed in config["seeds"]:
        partitions, audit, manifest = split_rows(benign, attack, seed, spec["grouping_policy"])
        require_evaluation_capacity(audit["sizes"], config["window_sizes"], config["attacker_ratios"])
        plans.append((seed, partitions, audit, manifest))
    texts = sorted({r["query"] for _, partitions, _, _ in plans
                    for classes in partitions.values() for rows in classes.values() for r in rows})
    positions = {text: i for i, text in enumerate(texts)}
    started = time.perf_counter()
    output.mkdir(parents=True, exist_ok=False)
    write_json(output / "config.json", config)
    identity = {"protocol": "fixed-window-grouped-reference-v1", "config": config, "dataset": spec,
                "data_sha256": {label: digest(json.dumps(rows, sort_keys=True, ensure_ascii=False))
                                for label, rows in (("benign", benign), ("attack", attack))},
                "code": code_identity(), "software": {"torch": torch.__version__, "numpy": np.__version__},
                "window_sampling": "without replacement within a draw; draws may overlap",
                "threshold_policy": "higher empirical quantile, strict score > threshold; not a finite-sample FPR guarantee",
                "status": "running"}
    write_json(output / "metadata.json", identity)
    try:
        encoded, encoder = embed_texts(texts, config["embedding_model"], config["embedding_revision"],
                                     config["query_prefix"], config["encode_batch_size"], config["device"],
                                     project_path(config["cache_dir"]))
        z = torch.as_tensor(encoded, dtype=getattr(torch, config["dtype"]), device=config["device"])
        summaries = []
        for seed, partitions, audit, manifest in plans:
            pools = {p: {label: np.array([positions[r["query"]] for r in rows], dtype=np.int64)
                         for label, rows in classes.items()} for p, classes in partitions.items()}
            bandwidth_seed = np.random.SeedSequence([seed, 0])
            ref = torch.as_tensor(pools["reference"]["benign"], device=z.device)
            sigma = median_bandwidth(z[ref], config["bandwidth_sample_size"], np.random.default_rng(bandwidth_seed))
            available = {"rbf": MMDDetector((sigma,)),
                         "multi_rbf": MMDDetector(tuple(sigma * s for s in (.5, 1, 2, 4)))}
            methods = {name: available[name] for name in config["methods"]}
            seed_dir = output / f"seed_{seed}"
            seed_dir.mkdir()
            write_json(seed_dir / "split_manifest.json", manifest)
            write_json(seed_dir / "split_audit.json", audit)
            for size in config["window_sizes"]:
                print(f"Seed {seed}, window {size}: calibrating and evaluating", flush=True)
                cal_rng, test_rng = [np.random.default_rng(s) for s in np.random.SeedSequence([seed, size, 1]).spawn(2)]
                calibration = make_windows(pools["calibration"]["benign"], [], pools["reference"]["benign"],
                                           size, config["reference_repeats"], config["calibration_windows"], [0], cal_rng)
                test = make_windows(pools["test"]["benign"], pools["test"]["attack"], pools["reference"]["benign"],
                                    size, config["reference_repeats"], config["test_windows"], [0] + config["attacker_ratios"], test_rng)
                rows, cal_rows, summary, thresholds = evaluate(methods, z, calibration, test, config["target_fpr"])
                destination = seed_dir / f"window_{size}"
                destination.mkdir()
                write_csv(destination / "scores.csv", rows)
                write_csv(destination / "calibration_scores.csv", cal_rows)
                draw_manifest = {phase: [{"split": w.split, "indices": w.indices.tolist(),
                                         "references": w.references.tolist()} for w in windows]
                                 for phase, windows in (("calibration", calibration), ("test", test))}
                write_json(destination / "draw_manifest.json", draw_manifest)
                write_json(destination / "metadata.json", {"median_bandwidth": sigma, "thresholds": thresholds,
                           "bandwidths": {name: method.bandwidths for name, method in methods.items()}})
                summaries.extend({"dataset": spec["name"], "seed": seed, "window_size": size, **row} for row in summary)
        write_csv(output / "summary.csv", summaries)
        write_json(output / "embedding_manifest.json", [digest(text) for text in texts])
        identity.update(status="complete", encoder=encoder, elapsed_seconds=time.perf_counter() - started)
        write_json(output / "metadata.json", identity)
    except Exception as exc:
        identity.update(status="failed", error=str(exc))
        write_json(output / "metadata.json", identity)
        raise
    print(f"Completed: {output / 'summary.csv'}", flush=True)
    return output


def main(argv=None):
    from experiments.cli import parse_config
    from experiments.workflow import execute
    parser, config, dry_run = parse_config(argv)
    try:
        execute(config, dry_run=dry_run)
    except (ValueError, OSError) as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    main()
