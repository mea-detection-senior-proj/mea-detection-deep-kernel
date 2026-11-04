"""Dataset-separated rates, paired differences and empirical endpoints."""
from collections import defaultdict
import math
import statistics


def _key(row):
    return row["dataset"], row["method"], int(row["seed"]), int(row["window_size"]), row["split"]


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


