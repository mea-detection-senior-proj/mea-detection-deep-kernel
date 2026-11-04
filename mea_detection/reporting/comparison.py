"""Validate locked evidence once, then derive every comparison output from it."""
from collections import defaultdict
import csv
import json
import math
from pathlib import Path

import numpy as np
from sklearn.metrics import roc_auc_score

from mea_detection.data.capacity import evaluation_capacity
from mea_detection.configuration import project_path
from mea_detection.experiments.artifacts import write_csv, write_json
from mea_detection.evaluation.comparison import _interpret
from mea_detection.evaluation.windows import calibration_threshold
from .render import _plots, _report


def _csv(path):
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def _split(ratio):
    return "heldout_benign" if ratio == 0 else "attacker" if ratio == 1 else f"mixed_{ratio:g}"


def _availability(lock):
    return [{"dataset": lock["dataset"]["name"], "seed": seed, "split": _split(ratio),
             **evaluation_capacity(lock["seeds"][str(seed)]["sizes"], size, ratio)}
            for seed in lock["settings"]["seeds"] for size in lock["settings"]["window_sizes"]
            for ratio in [0, *lock["settings"]["attacker_ratios"]]]


def _case_results(path, case, lock, methods):
    from mea_detection.experiments.protocol_io import load_draws
    directory = path / f"seed_{case['seed']}/window_{case['window_size']}"
    calibration, test = load_draws(project_path(lock["path"]) / case["draws"])
    if len(calibration) != lock["settings"]["calibration_windows"]:
        raise ValueError("Calibration window count differs from protocol")
    case_meta = json.loads((directory / "metadata.json").read_text(encoding="utf-8"))
    if case_meta["draws_sha256"] != lock["files"][case["draws"]] or case_meta["locked_draws"] != case["draws"]:
        raise ValueError("Case evaluation draws differ from protocol lock")
    scores, cal_scores = _csv(directory / "scores.csv"), _csv(directory / "calibration_scores.csv")
    if {(r["method"], int(r["window_id"])) for r in scores} != {(m, i) for m in methods for i in range(len(test))} or len(scores) != len(methods) * len(test):
        raise ValueError("Missing, duplicate or unexpected test scores")
    if {(r["method"], int(r["window_id"])) for r in cal_scores} != {(m, i) for m in methods for i in range(len(calibration))} or len(cal_scores) != len(methods) * len(calibration):
        raise ValueError("Missing, duplicate or unexpected calibration scores")
    rows, auc = [], []
    for method in methods:
        null = [float(r["score"]) for r in cal_scores if r["method"] == method]
        if not null or not all(math.isfinite(v) for v in null):
            raise ValueError("Non-finite or empty calibration scores")
        threshold = calibration_threshold(null, lock["settings"]["target_fpr"])
        if case_meta["thresholds"][method] != threshold or any(float(r["threshold"]) != threshold for r in cal_scores if r["method"] == method):
            raise ValueError("Calibration threshold differs from saved evidence")
        grouped = defaultdict(list)
        for row in (r for r in scores if r["method"] == method):
            window = test[int(row["window_id"])]
            value = float(row["score"])
            if (row["split"] != window.split or int(row["window_size"]) != len(window.indices)
                    or int(row["attacker_count"]) != window.attacker_count
                    or float(row["requested_ratio"]) != window.requested_ratio
                    or float(row["actual_ratio"]) != window.attacker_count / len(window.indices)):
                raise ValueError("Score window identity differs from locked draws")
            if not math.isfinite(value) or float(row["threshold"]) != threshold or int(row["suspicious"]) != int(value > threshold):
                raise ValueError("Invalid score, threshold or alert decision")
            grouped[window.split].append((value, int(row["suspicious"])))
        expected_splits = {_split(r) for r in [0, *lock["settings"]["attacker_ratios"]]
                           if evaluation_capacity(lock["seeds"][str(case["seed"])]["sizes"], case["window_size"], r)["supported"]}
        if set(grouped) != expected_splits or "heldout_benign" not in grouped:
            raise ValueError("Locked draws do not cover declared supported conditions")
        negative = [v for v, _ in grouped["heldout_benign"]]
        for split, entries in grouped.items():
            expected_count = lock["settings"]["test_windows"]
            if len(entries) != expected_count:
                raise ValueError("Test window count differs from protocol")
            alerts = sum(alert for _, alert in entries)
            rows.append({"dataset": lock["dataset"]["name"], "seed": case["seed"], "window_size": case["window_size"],
                         "method": method, "split": split, "windows": len(entries), "alerts": alerts,
                         "detection_rate": alerts / len(entries)})
            if split != "heldout_benign":
                positive = [v for v, _ in entries]
                auc.append({"dataset": lock["dataset"]["name"], "method": method, "seed": case["seed"],
                            "window_size": case["window_size"], "split": split,
                            "auroc": float(roc_auc_score([0] * len(negative) + [1] * len(positive), negative + positive))})
    return rows, auc


def _key(row):
    return row["dataset"], row["method"], int(row["seed"]), int(row["window_size"]), row["split"]


def _load_results(paths):
    from mea_detection.experiments.protocol_io import verify_lock
    runs, rows, auc, availability, locks = [], [], [], [], {}
    seen, method_sets = set(), defaultdict(set)
    sources = set()
    for path in map(lambda p: project_path(str(p)), paths):
        meta = json.loads((path / "metadata.json").read_text(encoding="utf-8"))
        if meta["status"] != "complete":
            raise ValueError(f"Incomplete run: {path}")
        config = json.loads((path / "config.json").read_text(encoding="utf-8"))
        lock = verify_lock(project_path(meta["protocol_lock"]), config, require_current_source=False)
        if meta.get("code") != lock.get("code") or not meta.get("code"):
            raise ValueError("Run source identity differs from protocol lock")
        source = meta["code"].get("pipeline_source_sha256")
        if not source:
            raise ValueError("Missing run source identity")
        sources.add(source)
        if len(sources) > 1:
            raise ValueError("Incompatible source identities across compared runs")
        dataset = lock["dataset"]["name"]
        if meta["lock_id"] != lock["lock_id"] or meta["dataset"] != lock["dataset"] or meta["protocol"] != lock["protocol"]:
            raise ValueError("Run identity differs from protocol lock")
        if dataset in locks and locks[dataset] != lock["lock_id"]:
            raise ValueError("Protocol lock IDs differ for the same dataset")
        if dataset not in locks:
            locks[dataset] = lock["lock_id"]
            availability.extend(_availability(lock))
        lock["path"] = meta["protocol_lock"]
        expected_cases = {(seed, size) for seed in lock["settings"]["seeds"] for size in lock["settings"]["window_sizes"]}
        locked_cases = {(c["seed"], c["window_size"]) for c in lock["cases"]}
        if locked_cases != expected_cases or len(lock["cases"]) != len(expected_cases):
            raise ValueError("Protocol cases differ from the declared seed/window grid")
        signatures = {(c["seed"], c["window_size"], c["draws_sha256"]) for c in meta["cases"]}
        expected = {(c["seed"], c["window_size"], lock["files"][c["draws"]]) for c in lock["cases"]}
        if signatures != expected or len(meta["cases"]) != len(expected):
            raise ValueError("Evaluation windows/references differ from the declared protocol")
        methods = config["methods"]
        if not methods or len(set(methods)) != len(methods):
            raise ValueError("Need distinct selected methods")
        reconstructed = []
        for case in lock["cases"]:
            case_rows, case_auc = _case_results(path, case, lock, methods)
            reconstructed.extend(case_rows)
            auc.extend(case_auc)
        summary = _csv(path / "summary.csv")
        by_key = {_key(r): r for r in summary}
        if len(by_key) != len(summary) or set(by_key) != {_key(r) for r in reconstructed}:
            raise ValueError("Summary coverage differs from locked score evidence")
        for row in reconstructed:
            key = _key(row)
            if key in seen:
                raise ValueError("Duplicate dataset/method/seed/window/split results")
            seen.add(key)
            saved = by_key[key]
            if (int(saved["windows"]) != row["windows"] or int(saved["alerts"]) != row["alerts"]
                    or not math.isclose(float(saved["detection_rate"]), row["detection_rate"], rel_tol=0, abs_tol=1e-15)):
                raise ValueError("Summary rates differ from per-window scores")
        method_sets[dataset].update(methods)
        rows.extend(reconstructed)
        runs.append({"path": str(path), "metadata": meta})
    if not rows:
        raise ValueError("No completed comparison results")
    if len({frozenset(m) for m in method_sets.values()}) != 1:
        raise ValueError("Datasets do not have identical selected methods")
    by_key = {_key(r): r for r in rows}
    for cell in availability:
        for method in method_sets[cell["dataset"]]:
            key = cell["dataset"], method, cell["seed"], cell["window_size"], cell["split"]
            if (key in by_key) != cell["supported"]:
                raise ValueError("Methods do not cover the declared supported conditions")
    return runs, rows, auc, availability, locks


def summarize(paths, output):
    output = project_path(str(output))
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite comparison: {output}")
    runs, rows, auc, availability, locks = _load_results(paths)
    aggregates, endpoints, paired = _interpret(rows, availability)
    output.mkdir(parents=True, exist_ok=False)
    metadata = {"status": "running", "lock_id": next(iter(locks.values())) if len(locks) == 1 else None,
                "lock_ids": locks, "runs": runs, "endpoint": {"minimum_tpr": .9, "maximum_measured_fpr": .05},
                "uncertainty": "Between-seed descriptive variation only; no independent-window confidence intervals",
                "operating_point": "Same calibration target; report measured FPR; no test threshold adjustment"}
    write_json(output / "metadata.json", metadata)
    try:
        for filename, values in (("per_seed.csv", rows), ("overall.csv", aggregates), ("minimum_windows.csv", endpoints),
                                 ("availability.csv", availability), ("auroc_per_seed.csv", auc), ("paired_differences.csv", paired)):
            if values:
                write_csv(output / filename, values)
        plots = _plots(aggregates, output)
        (output / "REPORT.md").write_text(_report(aggregates, endpoints, availability, plots), encoding="utf-8")
        metadata["status"] = "complete"
        write_json(output / "metadata.json", metadata)
    except Exception as exc:
        metadata.update(status="failed", error=str(exc))
        write_json(output / "metadata.json", metadata)
        raise
    print(f"Comparison: {output / 'REPORT.md'}")
    return output


