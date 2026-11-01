#!/usr/bin/env python3
import csv
import json
import math
from collections import defaultdict
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
OLD_ROOT = PROJECT_ROOT / "article" / "experiment" / "main"
NEW_ROOT = SCRIPT_DIR / "outputs"
RESULT_DIR = SCRIPT_DIR / "results"

METHOD_DIRS = {
    "MMD": "mmd",
    "Mahalanobis": "mahalanobis",
    "PRADA": "prada",
    "SEAT": "seat",
    "CAP": "cap",
    "DATE": "date",
}

METRICS = ["fpr", "tpr_5", "tpr_10", "tpr_25", "tpr_50", "tpr_100", "avg_tpr", "balanced_acc"]
RUN_FIELDS = ["source", "method", "dataset", "seed", "path", *METRICS]


def fmt(value: float) -> str:
    return "nan" if math.isnan(value) else f"{value:.6f}"


def mean(values: list[float]) -> float:
    values = [v for v in values if not math.isnan(v)]
    return sum(values) / len(values) if values else math.nan


def rate(groups: dict, key: str) -> float:
    try:
        return float(groups[key]["detection_rate"]) * 100.0
    except Exception:
        return math.nan


def read_metrics(path: Path, source: str, method: str, seed_hint: str = "") -> dict[str, str]:
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
    balanced_acc = (avg_tpr + 100.0 - fpr) / 2.0 if not math.isnan(avg_tpr) and not math.isnan(fpr) else math.nan
    return {
        "source": source,
        "method": method,
        "dataset": str(meta.get("dataset", path.parent.name)),
        "seed": str(meta.get("seed", seed_hint)),
        "path": str(path.relative_to(PROJECT_ROOT)),
        "fpr": fmt(fpr),
        "tpr_5": fmt(tprs["tpr_5"]),
        "tpr_10": fmt(tprs["tpr_10"]),
        "tpr_25": fmt(tprs["tpr_25"]),
        "tpr_50": fmt(tprs["tpr_50"]),
        "tpr_100": fmt(tprs["tpr_100"]),
        "avg_tpr": fmt(avg_tpr),
        "balanced_acc": fmt(balanced_acc),
    }


def collect_old() -> list[dict[str, str]]:
    rows = []
    for seed_dir in sorted(OLD_ROOT.glob("seed=*")):
        if not seed_dir.is_dir():
            continue
        seed = seed_dir.name.split("=", 1)[-1]
        for method in METHOD_DIRS:
            method_root = seed_dir / method
            if not method_root.exists():
                continue
            for path in sorted(method_root.glob("*/metadata.json")):
                rows.append(read_metrics(path, "old_article_main", method, seed))
    return rows


def collect_new() -> list[dict[str, str]]:
    rows = []
    for method, method_dir in METHOD_DIRS.items():
        root = NEW_ROOT / method_dir
        if not root.exists():
            continue
        for path in sorted(root.glob("*/metadata.json")):
            rows.append(read_metrics(path, "new_main", method))
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
                **{metric: fmt(mean([float(row[metric]) for row in group])) for metric in METRICS},
            }
        )
    return out


def compare(old_summary: list[dict[str, str]], new_summary: list[dict[str, str]]) -> list[dict[str, str]]:
    old_by_method = {row["method"]: row for row in old_summary}
    rows = []
    for new in new_summary:
        method = new["method"]
        old = old_by_method.get(method)
        if old is None:
            continue
        row = {"method": method, "old_runs": old["runs"], "new_runs": new["runs"]}
        for metric in METRICS:
            old_v = float(old[metric])
            new_v = float(new[metric])
            row[f"old_{metric}"] = fmt(old_v)
            row[f"new_{metric}"] = fmt(new_v)
            row[f"delta_{metric}"] = fmt(new_v - old_v)
        rows.append(row)
    return rows


def main() -> None:
    old_rows = collect_old()
    new_rows = collect_new()
    old_summary = aggregate(old_rows, "old_article_main")
    new_summary = aggregate(new_rows, "new_main")
    comparison = compare(old_summary, new_summary)

    write_csv(RESULT_DIR / "article_main_old_runs_recomputed.csv", old_rows, RUN_FIELDS)
    write_csv(RESULT_DIR / "article_main_new_runs_recomputed.csv", new_rows, RUN_FIELDS)
    write_csv(RESULT_DIR / "article_main_old_overall_recomputed.csv", old_summary, list(old_summary[0].keys()))
    write_csv(RESULT_DIR / "article_main_new_overall_recomputed.csv", new_summary, list(new_summary[0].keys()))
    write_csv(RESULT_DIR / "article_main_new_vs_old_overall.csv", comparison, list(comparison[0].keys()))

    print(f"old_runs={len(old_rows)} new_runs={len(new_rows)}")
    print(f"Wrote outputs under {RESULT_DIR}")


if __name__ == "__main__":
    main()
