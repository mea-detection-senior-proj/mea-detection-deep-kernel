"""Single-command orchestration with side-effect-free capacity preflight."""
import json

import numpy as np

from data_pipeline.datasets import load_dataset, split_rows
from data_pipeline.windows import attacker_count, make_windows
from experiments.configuration import ROOT, project_path
from experiments.artifacts import code_identity, write_json


def preflight(config):
    output = project_path(config["output"])
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite existing output: {output}")
    if config.get("protocol_lock"):
        from experiments.locked import verify_lock
        lock = verify_lock(project_path(config["protocol_lock"]), config)
        name = lock["dataset"]["name"]
        sizes_by_seed = {int(seed): details["sizes"] for seed, details in lock["seeds"].items()}
        protocol_action = "reuse verified protocol lock"
    else:
        spec, benign, attack = load_dataset(config, ROOT)
        sizes_by_seed = {}
        for seed in config["seeds"]:
            _, audit, _ = split_rows(benign, attack, seed, spec["grouping_policy"])
            sizes_by_seed[seed] = audit["sizes"]
        name = spec["name"]
        protocol_action = "prepare new shared protocol under output/protocol"
    for seed, sizes in sizes_by_seed.items():
        pools = {p: {label: np.arange(count) for label, count in classes.items()} for p, classes in sizes.items()}
        for size in config["window_sizes"]:
            try:
                make_windows(pools["calibration"]["benign"], [], pools["reference"]["benign"], size,
                             config["reference_repeats"], 1, [0], np.random.default_rng(0))
                make_windows(pools["test"]["benign"], pools["test"]["attack"], pools["reference"]["benign"], size,
                             config["reference_repeats"], 1, [0] + config["attacker_ratios"], np.random.default_rng(0))
            except ValueError as exc:
                raise ValueError(f"Dataset {name}, seed {seed}, evaluation window {size}: {exc}") from exc
        if "deep_kernel" in config["methods"]:
            required = config["training"]["window_size"]
            for part in ("train", "validation"):
                for label in ("benign", "attack"):
                    if sizes[part][label] < required:
                        raise ValueError(f"Seed {seed}: pure training needs {required} {part}/{label} rows, found {sizes[part][label]}")
    count = len(config["seeds"]) * len(config["window_sizes"])
    return {"dataset": name, "methods": config["methods"], "device": config["device"],
            "embedding_model": config["embedding_model"], "evaluation_window_sizes": config["window_sizes"],
            "seeds": config["seeds"], "seed_window_cases": count,
            "method_cases": count * len(config["methods"]),
            "training": config["training"] if "deep_kernel" in config["methods"] else "not selected",
            "reference_repeats": config["reference_repeats"], "calibration_windows_per_case": config["calibration_windows"],
            "test_windows_per_condition": config["test_windows"],
            "test_windows_per_case": config["test_windows"] * (1 + len(config["attacker_ratios"])),
            "actual_attack_conditions": [{"window_size": size, "requested_ratio": ratio,
                                          "attacker_count": attacker_count(size, ratio),
                                          "actual_ratio": attacker_count(size, ratio) / size}
                                         for size in config["window_sizes"] for ratio in config["attacker_ratios"]],
            "target_fpr": config["target_fpr"], "protocol_action": protocol_action,
            "output": str(output), "split_sizes": sizes_by_seed,
            "capacity_check": "passed; repeated windows may reuse queries",
            "device_check": "not allocated or checked by preflight"}


def execute(config, dry_run=False):
    plan = preflight(config)
    print(json.dumps(plan, indent=2, ensure_ascii=False), flush=True)
    if dry_run:
        return plan
    # Heavy work starts only after successful preflight.
    from experiments.locked import prepare, run_locked
    from experiments.summarize_comparison import summarize
    output = project_path(config["output"])
    output.mkdir(parents=True, exist_ok=False)
    write_json(output / "config.json", config)
    write_json(output / "plan.json", plan)
    status = {"status": "running", "phase": "preparing", "code": code_identity()}
    write_json(output / "run.json", status)
    try:
        lock_path = project_path(config["protocol_lock"]) if config.get("protocol_lock") else prepare(config, output / "protocol")
        effective = {**config, "protocol_lock": str(lock_path), "output": str(output / "results")}
        write_json(output / "resolved_config.json", effective)
        status.update(phase="running selected methods", protocol_lock=str(lock_path))
        write_json(output / "run.json", status)
        run_locked(effective)
        status["phase"] = "summarizing"
        write_json(output / "run.json", status)
        summarize([output / "results"], output / "report")
        status.update(status="complete", phase="complete")
        write_json(output / "run.json", status)
    except Exception as exc:
        status.update(status="failed", error=str(exc))
        write_json(output / "run.json", status)
        raise
    print(f"Finished: {output / 'report' / 'REPORT.md'}", flush=True)
    return output
