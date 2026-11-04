"""Render comparison tables, plots and an English report."""

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


