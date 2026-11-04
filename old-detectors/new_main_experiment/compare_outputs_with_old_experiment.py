#!/usr/bin/env python3
import csv
import json
import math
from collections import defaultdict
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent

OLD_SOURCES = {
    "MMD": PROJECT_ROOT / "experiment_result" / "MMD" / "1",
    "Mahalanobis": PROJECT_ROOT / "experiment_result" / "Mahalanobis" / "1",
    "CAP": PROJECT_ROOT / "experiment_result" / "cap" / "two-side",
    "DATE": PROJECT_ROOT / "experiment_result" / "date" / "two-side",
    "PRADA": PROJECT_ROOT / "experiment_result" / "prada" / "two-side",
    "SEAT": PROJECT_ROOT / "experiment_result" / "seat" / "two-side",
}

NEW_OUTPUTS = SCRIPT_DIR / "outputs"
RESULT_DIR = SCRIPT_DIR / "results"

RUN_FIELDS = [
    "source",
    "method",
    "dataset",
    "seed",
    "path",
    "fpr",
    "tpr_5",
    "tpr_10",
    "tpr_25",
    "tpr_50",
    "tpr_100",
    "avg_tpr",
    "balanced_acc",
]

RATIO_FIELDS = [
    ("0", "fpr"),
    ("0.05", "tpr_5"),
    ("0.1", "tpr_10"),
    ("0.25", "tpr_25"),
    ("0.5", "tpr_50"),
    ("1", "tpr_100"),
]


def rate(groups: dict, key: str) -> float:
    try:
        return float(groups[key]["detection_rate"]) * 100.0
    except Exception:
        return math.nan


def mean(values: list[float]) -> float:
    values = [v for v in values if not math.isnan(v)]
    return sum(values) / len(values) if values else math.nan


def fmt(value: float) -> str:
    return "nan" if math.isnan(value) else f"{value:.6f}"


def read_metrics(path: Path, source: str, method: str) -> dict[str, str]:
    meta = json.loads(path.read_text(encoding="utf-8"))
    groups = meta.get("metrics_by_split") or meta.get("metrics_by_family") or {}
    fpr = rate(groups, "heldout_benign")
    tprs = {
        "tpr_5": rate(groups, "mixed_0.05"),
        "tpr_10": rate(groups, "mixed_0.1"),
        "tpr_25": rate(groups, "mixed_0.25"),
        "tpr_50": rate(groups, "mixed_0.5"),
        "tpr_100": rate(groups, "attacker"),
    }
    avg_tpr = mean(list(tprs.values()))
    balanced = (avg_tpr + 100.0 - fpr) / 2.0 if not math.isnan(avg_tpr) and not math.isnan(fpr) else math.nan
    return {
        "source": source,
        "method": method,
        "dataset": str(meta.get("dataset", path.parent.name)),
        "seed": str(meta.get("seed", "")),
        "path": str(path.relative_to(PROJECT_ROOT)),
        "fpr": fmt(fpr),
        "tpr_5": fmt(tprs["tpr_5"]),
        "tpr_10": fmt(tprs["tpr_10"]),
        "tpr_25": fmt(tprs["tpr_25"]),
        "tpr_50": fmt(tprs["tpr_50"]),
        "tpr_100": fmt(tprs["tpr_100"]),
        "avg_tpr": fmt(avg_tpr),
        "balanced_acc": fmt(balanced),
    }


def collect_old() -> list[dict[str, str]]:
    rows = []
    for method, root in OLD_SOURCES.items():
        for path in sorted(root.glob("*/metadata.json")):
            rows.append(read_metrics(path, "old", method))
    return rows


def collect_new() -> list[dict[str, str]]:
    rows = []
    method_map = {
        "mmd": "MMD",
        "mahalanobis": "Mahalanobis",
        "cap": "CAP",
        "date": "DATE",
        "prada": "PRADA",
        "seat": "SEAT",
    }
    for method_dir, method in method_map.items():
        root = NEW_OUTPUTS / method_dir
        if not root.exists():
            continue
        for path in sorted(root.glob("*/metadata.json")):
            rows.append(read_metrics(path, "new", method))
    return rows


def write_csv(path: Path, rows: list[dict[str, str]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def aggregate(rows: list[dict[str, str]], source: str) -> list[dict[str, str]]:
    groups = defaultdict(list)
    for row in rows:
        groups[row["method"]].append(row)

    out = []
    for method in sorted(groups):
        group = groups[method]
        out.append(
            {
                "source": source,
                "method": method,
                "runs": str(len(group)),
                "fpr": fmt(mean([float(r["fpr"]) for r in group])),
                "tpr_5": fmt(mean([float(r["tpr_5"]) for r in group])),
                "tpr_10": fmt(mean([float(r["tpr_10"]) for r in group])),
                "tpr_25": fmt(mean([float(r["tpr_25"]) for r in group])),
                "tpr_50": fmt(mean([float(r["tpr_50"]) for r in group])),
                "tpr_100": fmt(mean([float(r["tpr_100"]) for r in group])),
                "avg_tpr": fmt(mean([float(r["avg_tpr"]) for r in group])),
                "balanced_acc": fmt(mean([float(r["balanced_acc"]) for r in group])),
            }
        )
    return out


def compare(old_summary: list[dict[str, str]], new_summary: list[dict[str, str]]) -> list[dict[str, str]]:
    old_by_method = {r["method"]: r for r in old_summary}
    rows = []
    for new in new_summary:
        method = new["method"]
        old = old_by_method.get(method)
        if old is None:
            continue
        row = {
            "method": method,
            "old_runs": old["runs"],
            "new_runs": new["runs"],
        }
        for metric in ["fpr", "tpr_5", "tpr_10", "tpr_25", "tpr_50", "tpr_100", "avg_tpr", "balanced_acc"]:
            old_v = float(old[metric])
            new_v = float(new[metric])
            row[f"old_{metric}"] = fmt(old_v)
            row[f"new_{metric}"] = fmt(new_v)
            row[f"delta_{metric}"] = fmt(new_v - old_v)
        rows.append(row)
    return rows


def compare_by_ratio(old_rows: list[dict[str, str]], new_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    old_summary = {r["method"]: r for r in aggregate(old_rows, "old")}
    new_summary = {r["method"]: r for r in aggregate(new_rows, "new")}
    out = []
    for method in sorted(set(old_summary) & set(new_summary)):
        old = old_summary[method]
        new = new_summary[method]
        for ratio, metric in RATIO_FIELDS:
            old_v = float(old[metric])
            new_v = float(new[metric])
            out.append(
                {
                    "method": method,
                    "ratio": ratio,
                    "old_detection_rate": fmt(old_v),
                    "new_detection_rate": fmt(new_v),
                    "delta_detection_rate": fmt(new_v - old_v),
                }
            )
    return out


def main() -> None:
    old_rows = collect_old()
    new_rows = collect_new()
    old_summary = aggregate(old_rows, "old")
    new_summary = aggregate(new_rows, "new")
    comparison = compare(old_summary, new_summary)
    ratio_comparison = compare_by_ratio(old_rows, new_rows)

    write_csv(RESULT_DIR / "old_outputs_recomputed_runs.csv", old_rows, RUN_FIELDS)
    write_csv(RESULT_DIR / "new_outputs_recomputed_runs.csv", new_rows, RUN_FIELDS)
    write_csv(RESULT_DIR / "old_outputs_recomputed_overall.csv", old_summary, list(old_summary[0].keys()))
    write_csv(RESULT_DIR / "new_outputs_recomputed_overall.csv", new_summary, list(new_summary[0].keys()))
    write_csv(RESULT_DIR / "new_vs_old_outputs_recomputed_overall.csv", comparison, list(comparison[0].keys()))
    write_csv(
        RESULT_DIR / "new_vs_old_outputs_recomputed_by_ratio.csv",
        ratio_comparison,
        ["method", "ratio", "old_detection_rate", "new_detection_rate", "delta_detection_rate"],
    )

    print(f"old_runs={len(old_rows)} new_runs={len(new_rows)}")
    print(f"Wrote outputs under {RESULT_DIR}")


if __name__ == "__main__":
    main()
