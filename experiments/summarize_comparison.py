"""Validate locked evidence once, then derive every comparison output from it."""
import argparse
from collections import defaultdict
import csv
import json
import math
from pathlib import Path
import statistics

import numpy as np
from sklearn.metrics import roc_auc_score

from data_pipeline.capacity import evaluation_capacity
from experiments.configuration import project_path
from experiments.artifacts import write_csv, write_json


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
    from experiments.locked import load_draws
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
        threshold = float(np.quantile(null, 1 - lock["settings"]["target_fpr"], method="higher"))
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
    from experiments.locked import verify_lock
    runs, rows, auc, availability, locks = [], [], [], [], {}
    seen, method_sets = set(), defaultdict(set)
    for path in map(lambda p: project_path(str(p)), paths):
        meta = json.loads((path / "metadata.json").read_text(encoding="utf-8"))
        if meta["status"] != "complete":
            raise ValueError(f"Incomplete run: {path}")
        config = json.loads((path / "config.json").read_text(encoding="utf-8"))
        lock = verify_lock(project_path(meta["protocol_lock"]), config)
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


def _interpret(rows, availability):
    by_key = {_key(r): r for r in rows}
    for row in rows:
        row["measured_fpr"] = by_key[(row["dataset"], row["method"], row["seed"], row["window_size"], "heldout_benign")]["detection_rate"]
    groups = defaultdict(list)
    for row in rows:
        groups[(row["dataset"], row["method"], row["window_size"], row["split"])].append(row)
    aggregates = []
    for (dataset, method, size, split), selected in sorted(groups.items()):
        values = [r["detection_rate"] for r in selected]
        aggregates.append({"dataset": dataset, "method": method, "window_size": size, "split": split,
                           "seeds": len(values), "rate_mean": statistics.mean(values),
                           "rate_std_between_seeds": statistics.stdev(values) if len(values) > 1 else None,
                           "rate_min": min(values), "rate_max": max(values),
                           "measured_fpr_mean": statistics.mean(r["measured_fpr"] for r in selected)})
    endpoints = []
    for dataset, method, seed in sorted({(r["dataset"], r["method"], r["seed"]) for r in rows}):
        cells = [c for c in availability if c["dataset"] == dataset and c["seed"] == seed and c["split"] != "heldout_benign"]
        for split in sorted({c["split"] for c in cells}):
            supported = [by_key[(dataset, method, seed, c["window_size"], split)] for c in cells if c["split"] == split and c["supported"]]
            qualifying = [r for r in supported if r["detection_rate"] >= .9 and r["measured_fpr"] <= .05]
            best = min(qualifying, key=lambda r: r["window_size"]) if qualifying else None
            endpoints.append({"dataset": dataset, "seed": seed, "method": method, "split": split,
                              "attacker_fraction": next(c["requested_ratio"] for c in cells if c["split"] == split),
                              "status": "reached" if best else "not_reached" if supported else "unavailable",
                              "minimum_effective_window_size": best["window_size"] if best else None,
                              "tpr": best["detection_rate"] if best else None,
                              "measured_fpr": best["measured_fpr"] if best else None})
    paired = []
    for dataset, size, split in sorted({(r["dataset"], r["window_size"], r["split"]) for r in rows}):
        deep = {r["seed"]: r["detection_rate"] for r in rows if (r["dataset"], r["method"], r["window_size"], r["split"]) == (dataset, "deep_kernel", size, split)}
        for baseline in sorted({r["method"] for r in rows} - {"deep_kernel"}):
            base = {r["seed"]: r["detection_rate"] for r in rows if (r["dataset"], r["method"], r["window_size"], r["split"]) == (dataset, baseline, size, split)}
            if deep and base:
                diffs = [deep[seed] - base[seed] for seed in sorted(deep)]
                paired.append({"dataset": dataset, "baseline": baseline, "window_size": size, "split": split,
                               "deep_minus_baseline_mean": statistics.mean(diffs),
                               "deep_minus_baseline_min": min(diffs), "deep_minus_baseline_max": max(diffs)})
    return aggregates, endpoints, paired


def _plots(aggregates, output):
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    from matplotlib.figure import Figure
    plots = []
    for index, (dataset, split) in enumerate(sorted({(r["dataset"], r["split"]) for r in aggregates if r["split"] != "heldout_benign"})):
        figure = Figure(figsize=(9, 5), layout="constrained")
        FigureCanvasAgg(figure)
        tpr, fpr = figure.subplots(1, 2, sharey=True)
        for method in sorted({r["method"] for r in aggregates if r["dataset"] == dataset}):
            selected = sorted((r for r in aggregates if (r["dataset"], r["method"], r["split"]) == (dataset, method, split)), key=lambda r: r["window_size"])
            for axis, metric in ((tpr, "rate_mean"), (fpr, "measured_fpr_mean")):
                axis.plot([r["window_size"] for r in selected], [r[metric] for r in selected], marker="o", label=method)
        for axis, label, target in ((tpr, "Measured TPR", .9), (fpr, "Measured FPR", .05)):
            axis.axhline(target, color="gray", linestyle="--", linewidth=1)
            axis.set(xlabel="Window size", ylabel=label, ylim=(-.02, 1.02))
            axis.set_xticks(sorted({r["window_size"] for r in aggregates if r["dataset"] == dataset}))
            axis.grid(alpha=.2)
        tpr.legend(fontsize=8)
        figure.suptitle(f"{dataset} / {split} — descriptive seed means")
        filename = f"rates_{index + 1}.png"
        figure.savefig(output / filename, dpi=150)
        plots.append((dataset, split, filename))
    return plots


def _report(aggregates, endpoints, availability, plots):
    lines = ["# Locked comparison", "", "Adapted common evaluation protocol; not an unchanged reproduction of the original full detector.",
             "Rates are percentages. Variation is descriptive sample SD across seeds, not a confidence interval.",
             "For a single seed only the mean is shown; between-seed variation cannot be estimated.",
             "Repeated draws reuse finite pools; they do not establish source-population uncertainty or population FPR control.", ""]
    for dataset in sorted({r["dataset"] for r in aggregates}):
        selected = [r for r in aggregates if r["dataset"] == dataset]
        lines += [f"## {dataset}", "", "| Window | Method | Condition | Seeds | Rate (mean and sample SD) | Paired benign FPR (mean) |", "|---:|---|---|---:|---:|---:|"]
        for row in selected:
            label = "Benign FPR" if row["split"] == "heldout_benign" else f"TPR {100 * (1 if row['split'] == 'attacker' else float(row['split'][6:])):g}%"
            value = f"{100 * row['rate_mean']:.2f}"
            if row["seeds"] > 1:
                value += f" ± {100 * row['rate_std_between_seeds']:.2f}"
            lines.append(f"| {row['window_size']} | {row['method']} | {label} | {row['seeds']} | {value} | {100 * row['measured_fpr_mean']:.2f} |")
        lines += ["", "### Per-seed minimum effective window size", "",
                  "Requires measured TPR >= 90% AND measured FPR <= 5%. Only tested supported sizes qualify; no interpolation.",
                  "not_reached: supported sizes exist but none qualifies. unavailable: no supported size exists.", "",
                  "| Seed | Method | Attack fraction | Status | Minimum window | TPR | Measured FPR |", "|---:|---|---:|---|---:|---:|---:|"]
        for row in (r for r in endpoints if r["dataset"] == dataset):
            values = [str(row["minimum_effective_window_size"]) if row["minimum_effective_window_size"] is not None else "—",
                      f"{100 * row['tpr']:.2f}" if row["tpr"] is not None else "—",
                      f"{100 * row['measured_fpr']:.2f}" if row["measured_fpr"] is not None else "—"]
            lines.append(f"| {row['seed']} | {row['method']} | {100 * row['attacker_fraction']:g}% | {row['status']} | " + " | ".join(values) + " |")
        unavailable = [c for c in availability if c["dataset"] == dataset and not c["supported"]]
        if unavailable:
            lines += ["", "### Unavailable conditions (all methods)", "", "| Seed | Window | Condition | Reason |", "|---:|---:|---|---|"]
            lines += [f"| {c['seed']} | {c['window_size']} | {c['split']} | {c['shortages']} |" for c in unavailable]
        for name, split, filename in plots:
            if name == dataset:
                lines += ["", f"![{dataset} {split}: TPR and measured FPR]({filename})"]
    lines += ["", "Full per-seed rates and paired measured FPR: per_seed.csv. Availability: availability.csv.",
              "All compared methods use the same verified locked windows and reference draws within each dataset.",
              "Same nominal calibration target does not prove matched measured FPR. No test threshold adjustment.",
              "Thresholds use benign calibration; learned checkpoint selection uses validation.",
              "No unseen-family or cross-dataset transfer claim. Existing datasets are development-exposed benchmarks."]
    return "\n".join(lines) + "\n"


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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs", nargs="+", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    summarize(args.runs, args.output)


if __name__ == "__main__":
    main()
