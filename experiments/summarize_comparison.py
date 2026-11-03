"""Compare completed baseline/deep runs only when locked evaluation draws match."""
import argparse
import csv
import json
from pathlib import Path
import statistics

from sklearn.metrics import roc_auc_score

from experiments.configuration import project_path
from experiments.artifacts import write_csv, write_json


def summarize(paths, output):
    output = project_path(str(output))
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite comparison: {output}")
    runs, rows, auc_rows = [], [], []
    conditions, lock_ids = None, set()
    for path in map(lambda p: project_path(str(p)), paths):
        meta = json.loads((path / "metadata.json").read_text(encoding="utf-8"))
        if meta["status"] != "complete":
            raise ValueError(f"Incomplete run: {path}")
        signatures = {(c["seed"], c["window_size"], c["draws_sha256"]) for c in meta["cases"]}
        if conditions is not None and conditions != signatures:
            raise ValueError("Evaluation windows/references differ between runs")
        conditions = signatures
        lock_ids.add(meta["lock_id"])
        runs.append({"path": str(path), "metadata": meta})
        with (path / "summary.csv").open(encoding="utf-8", newline="") as stream:
            for row in csv.DictReader(stream):
                rows.append({**row, "seed": int(row["seed"]), "window_size": int(row["window_size"]),
                             "detection_rate": float(row["detection_rate"])})
        for case in meta["cases"]:
            with (path / f"seed_{case['seed']}/window_{case['window_size']}/scores.csv").open(encoding="utf-8", newline="") as stream:
                scores = list(csv.DictReader(stream))
            for method in {r["method"] for r in scores}:
                negative = [float(r["score"]) for r in scores if r["method"] == method and r["split"] == "heldout_benign"]
                for split in {r["split"] for r in scores if r["split"] != "heldout_benign"}:
                    positive = [float(r["score"]) for r in scores if r["method"] == method and r["split"] == split]
                    if positive:
                        auc_rows.append({"method": method, "seed": case["seed"], "window_size": case["window_size"],
                                         "split": split, "auroc": float(roc_auc_score([0] * len(negative) + [1] * len(positive), negative + positive))})
    if len(lock_ids) != 1:
        raise ValueError("Protocol lock IDs differ")
    keys = [(r["method"], r["seed"], r["window_size"], r["split"]) for r in rows]
    if len(set(keys)) != len(keys):
        raise ValueError("Duplicate method/seed/window/split results")
    expected = {(r["seed"], r["window_size"], r["split"]) for r in rows}
    for method in {r["method"] for r in rows}:
        if {(r["seed"], r["window_size"], r["split"]) for r in rows if r["method"] == method} != expected:
            raise ValueError("Methods do not have identical evaluation conditions")
    aggregates = []
    for method, size, split in sorted({(r["method"], r["window_size"], r["split"]) for r in rows}):
        selected = [r for r in rows if (r["method"], r["window_size"], r["split"]) == (method, size, split)]
        values = [r["detection_rate"] for r in selected]
        aggregates.append({"method": method, "window_size": size, "split": split, "seeds": len(values),
                           "rate_mean": statistics.mean(values), "rate_std_between_seeds": statistics.stdev(values) if len(values) > 1 else None,
                           "rate_min": min(values), "rate_max": max(values)})
    paired = []
    selected_methods = {r["method"] for r in rows}
    for baseline in ("rbf", "multi_rbf"):
        if "deep_kernel" not in selected_methods or baseline not in selected_methods:
            continue
        for size, split in sorted({(r["window_size"], r["split"]) for r in rows}):
            deep = {r["seed"]: r["detection_rate"] for r in rows if (r["method"], r["window_size"], r["split"]) == ("deep_kernel", size, split)}
            base = {r["seed"]: r["detection_rate"] for r in rows if (r["method"], r["window_size"], r["split"]) == (baseline, size, split)}
            if not deep or deep.keys() != base.keys():
                raise ValueError("Need paired Deep Kernel and baseline results")
            diffs = [deep[seed] - base[seed] for seed in deep]
            paired.append({"baseline": baseline, "window_size": size, "split": split,
                           "deep_minus_baseline_mean": statistics.mean(diffs),
                           "deep_minus_baseline_min": min(diffs), "deep_minus_baseline_max": max(diffs)})
    output.mkdir(parents=True, exist_ok=False)
    write_csv(output / "per_seed.csv", rows)
    write_csv(output / "overall.csv", aggregates)
    if paired:
        write_csv(output / "paired_differences.csv", paired)
    write_csv(output / "auroc_per_seed.csv", auc_rows)
    write_json(output / "metadata.json", {"lock_id": next(iter(lock_ids)), "runs": runs,
               "uncertainty": "Between-seed descriptive variation only; no independent-window confidence intervals",
               "operating_point": "Same calibration target, report actual held-out FPR; no test threshold adjustment"})
    dataset_names = ", ".join(sorted({r["dataset"] for r in rows}))
    splits = {r["split"] for r in aggregates}
    columns = (["heldout_benign"] if "heldout_benign" in splits else [])
    columns += sorted((s for s in splits if s.startswith("mixed_")), key=lambda s: float(s[6:]))
    columns += ["attacker"] if "attacker" in splits else []
    labels = ["Benign FPR" if s == "heldout_benign" else "TPR 100%" if s == "attacker"
              else f"TPR {float(s[6:]) * 100:g}%" for s in columns]
    lines = [f"# Locked comparison: {dataset_names}", "",
             "Rates are percentages. Variation is descriptive across split/training seeds, not a confidence interval.",
             "For a single seed only the mean is shown; between-seed variation cannot be estimated.", "",
             "| Window | Method | " + " | ".join(labels) + " |",
             "|---:|---|" + "---:|" * len(labels)]
    for size in sorted({r["window_size"] for r in aggregates}):
        for method in ("rbf", "multi_rbf", "deep_kernel"):
            if method not in selected_methods:
                continue
            by = {r["split"]: r for r in aggregates if r["window_size"] == size and r["method"] == method}
            values = [((f"{100 * by[split]['rate_mean']:.2f} ± {100 * by[split]['rate_std_between_seeds']:.2f}"
                        if by[split]["seeds"] > 1 else f"{100 * by[split]['rate_mean']:.2f}")
                       if split in by else "not evaluated")
                      for split in columns]
            lines.append(f"| {size} | {method} | " + " | ".join(values) + " |")
    lines += ["", "All methods use exactly the same locked windows and reference draws.",
              "Same nominal calibration target does not prove matched measured FPR.",
              "No unseen-family or cross-dataset claim.",
              "Thresholds use benign calibration; Deep Kernel checkpoint selection uses validation."]
    (output / "REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
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
