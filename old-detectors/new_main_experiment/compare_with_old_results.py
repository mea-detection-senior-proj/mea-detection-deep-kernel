#!/usr/bin/env python3
import csv
import json
import math
from collections import defaultdict
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent

RESULT_DIR = SCRIPT_DIR / "results"
ROW_DIR = RESULT_DIR / "rows"
OLD_DIR = PROJECT_ROOT / "experiment_result" / "summary"

NEW_RUNS = RESULT_DIR / "new_main_experiment_runs_bs1500.csv"
NEW_OVERALL = RESULT_DIR / "new_main_experiment_overall_non_date_bs1500.csv"
NEW_BY_RATIO = RESULT_DIR / "new_main_experiment_by_ratio_non_date_bs1500.csv"
COMPARE_OVERALL = RESULT_DIR / "new_vs_old_overall_common_methods_bs1500.csv"
COMPARE_BY_RATIO = RESULT_DIR / "new_vs_old_by_ratio_common_methods_bs1500.csv"

RATIO_FIELDS = [
    ("0", "benign_fpr"),
    ("0.05", "5pct_tpr"),
    ("0.1", "10pct_tpr"),
    ("0.25", "25pct_tpr"),
    ("0.5", "50pct_tpr"),
    ("1", "100pct_tpr"),
]

RUN_FIELDS = [
    "method",
    "dataset",
    "seed",
    "batch_size",
    "embedding_model",
    "query_prefix",
    "mmd_reference_repeats",
    "mmd_null_samples",
    "benign_fpr",
    "5pct_tpr",
    "10pct_tpr",
    "25pct_tpr",
    "50pct_tpr",
    "100pct_tpr",
    "avg_tpr",
    "balanced_acc",
    "output_dir",
    "metadata_path",
    "log_file",
    "status",
]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def read_row_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f, fieldnames=RUN_FIELDS))


def write_csv(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def mean(vals: list[float]) -> float:
    return sum(vals) / len(vals) if vals else math.nan


def pct_to_rate(value: str) -> float:
    return float(value) / 100.0


def fmt(value: float) -> str:
    return "nan" if math.isnan(value) else f"{value:.6f}"


def is_nan_text(value: str) -> bool:
    try:
        return math.isnan(float(value))
    except Exception:
        return True


def rate(group: dict, key: str) -> float:
    try:
        return float(group[key]["detection_rate"]) * 100.0
    except Exception:
        return math.nan


def fill_metrics_from_metadata(row: dict[str, str]) -> dict[str, str]:
    if not is_nan_text(row.get("benign_fpr", "nan")):
        return row

    path = Path(row.get("metadata_path", ""))
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    if not path.exists():
        return row

    meta = json.loads(path.read_text(encoding="utf-8"))
    groups = meta.get("metrics_by_split") or meta.get("metrics_by_family") or {}
    fpr = rate(groups, "heldout_benign")
    tprs = {
        "5pct_tpr": rate(groups, "mixed_0.05"),
        "10pct_tpr": rate(groups, "mixed_0.1"),
        "25pct_tpr": rate(groups, "mixed_0.25"),
        "50pct_tpr": rate(groups, "mixed_0.5"),
        "100pct_tpr": rate(groups, "attacker"),
    }
    vals = [value for value in tprs.values() if not math.isnan(value)]
    avg = mean(vals)
    bal = (avg + 100.0 - fpr) / 2.0 if not math.isnan(avg) and not math.isnan(fpr) else math.nan

    row["benign_fpr"] = fmt(fpr)
    for key, value in tprs.items():
        row[key] = fmt(value)
    row["avg_tpr"] = fmt(avg)
    row["balanced_acc"] = fmt(bal)
    return row


def load_new_rows() -> list[dict[str, str]]:
    rows = []
    failures = []
    for path in sorted(ROW_DIR.iterdir()):
        try:
            parsed = read_row_csv(path)
            if parsed:
                rows.extend(fill_metrics_from_metadata(row) for row in parsed)
        except Exception as exc:
            failures.append((path, exc))
    if not rows and failures:
        first_path, first_exc = failures[0]
        print(f"First row read failure: {first_path}: {first_exc}")
    return rows


def main() -> None:
    rows = load_new_rows()
    if not rows:
        exists = ROW_DIR.exists()
        sample = list(ROW_DIR.iterdir())[:5] if exists else []
        sample_text = ", ".join(str(path) for path in sample) if sample else "N/A"
        raise SystemExit(
            f"No row CSV files found under {ROW_DIR}\n"
            f"ROW_DIR exists: {exists}\n"
            f"Sample entries: {sample_text}"
        )

    fields = list(rows[0].keys())
    write_csv(NEW_RUNS, rows, fields)

    completed = [r for r in rows if r.get("status") == "0"]
    non_date = [r for r in completed if r["method"] != "DATE"]

    by_method: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in non_date:
        by_method[row["method"]].append(row)

    overall_rows = []
    for method in sorted(by_method):
        group = by_method[method]
        fpr = mean([pct_to_rate(r["benign_fpr"]) for r in group])
        attack = mean([pct_to_rate(r["avg_tpr"]) for r in group])
        bal = (attack + 1.0 - fpr) / 2.0
        overall_rows.append(
            {
                "detector": method,
                "runs": len(group),
                "false_positive_rate": fmt(fpr),
                "avg_attack_detection_rate": fmt(attack),
                "balanced_accuracy": fmt(bal),
                "5pct_tpr": fmt(mean([pct_to_rate(r["5pct_tpr"]) for r in group])),
                "10pct_tpr": fmt(mean([pct_to_rate(r["10pct_tpr"]) for r in group])),
                "25pct_tpr": fmt(mean([pct_to_rate(r["25pct_tpr"]) for r in group])),
                "50pct_tpr": fmt(mean([pct_to_rate(r["50pct_tpr"]) for r in group])),
                "100pct_tpr": fmt(mean([pct_to_rate(r["100pct_tpr"]) for r in group])),
            }
        )

    write_csv(
        NEW_OVERALL,
        overall_rows,
        [
            "detector",
            "runs",
            "false_positive_rate",
            "avg_attack_detection_rate",
            "balanced_accuracy",
            "5pct_tpr",
            "10pct_tpr",
            "25pct_tpr",
            "50pct_tpr",
            "100pct_tpr",
        ],
    )

    ratio_rows = []
    for method in sorted(by_method):
        group = by_method[method]
        for ratio, field in RATIO_FIELDS:
            ratio_rows.append(
                {
                    "detector": method,
                    "ratio": ratio,
                    "runs": len(group),
                    "detection_rate": fmt(mean([pct_to_rate(r[field]) for r in group])),
                }
            )
    write_csv(NEW_BY_RATIO, ratio_rows, ["detector", "ratio", "runs", "detection_rate"])

    old_overall = {r["detector"]: r for r in read_csv(OLD_DIR / "overall_metrics.csv")}
    compare_rows = []
    for row in overall_rows:
        method = row["detector"]
        if method not in old_overall:
            continue
        old = old_overall[method]
        new_fpr = float(row["false_positive_rate"])
        old_fpr = float(old["false_positive_rate"])
        new_attack = float(row["avg_attack_detection_rate"])
        old_attack = float(old["avg_attack_detection_rate"])
        new_bal = float(row["balanced_accuracy"])
        old_bal = float(old["balanced_accuracy"])
        compare_rows.append(
            {
                "detector": method,
                "old_false_positive_rate": fmt(old_fpr),
                "new_false_positive_rate": fmt(new_fpr),
                "delta_false_positive_rate": fmt(new_fpr - old_fpr),
                "old_avg_attack_detection_rate": fmt(old_attack),
                "new_avg_attack_detection_rate": fmt(new_attack),
                "delta_avg_attack_detection_rate": fmt(new_attack - old_attack),
                "old_balanced_accuracy": fmt(old_bal),
                "new_balanced_accuracy": fmt(new_bal),
                "delta_balanced_accuracy": fmt(new_bal - old_bal),
            }
        )
    write_csv(
        COMPARE_OVERALL,
        compare_rows,
        [
            "detector",
            "old_false_positive_rate",
            "new_false_positive_rate",
            "delta_false_positive_rate",
            "old_avg_attack_detection_rate",
            "new_avg_attack_detection_rate",
            "delta_avg_attack_detection_rate",
            "old_balanced_accuracy",
            "new_balanced_accuracy",
            "delta_balanced_accuracy",
        ],
    )

    old_ratio = {
        (r["detector"], r["ratio"]): r for r in read_csv(OLD_DIR / "overall_by_detector_ratio.csv")
    }
    compare_ratio_rows = []
    for row in ratio_rows:
        key = (row["detector"], row["ratio"])
        if key not in old_ratio:
            continue
        old_rate = float(old_ratio[key]["detection_rate"])
        new_rate = float(row["detection_rate"])
        compare_ratio_rows.append(
            {
                "detector": row["detector"],
                "ratio": row["ratio"],
                "old_detection_rate": fmt(old_rate),
                "new_detection_rate": fmt(new_rate),
                "delta_detection_rate": fmt(new_rate - old_rate),
            }
        )
    write_csv(
        COMPARE_BY_RATIO,
        compare_ratio_rows,
        ["detector", "ratio", "old_detection_rate", "new_detection_rate", "delta_detection_rate"],
    )

    print(f"Wrote {NEW_RUNS}")
    print(f"Wrote {NEW_OVERALL}")
    print(f"Wrote {NEW_BY_RATIO}")
    print(f"Wrote {COMPARE_OVERALL}")
    print(f"Wrote {COMPARE_BY_RATIO}")


if __name__ == "__main__":
    main()
