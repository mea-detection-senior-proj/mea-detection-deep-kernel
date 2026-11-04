# Known-attack pilot: model_leeching

Exploratory run, 2026-10-28. This is not a definitive comparison at equal FPR.

## Setup

- Protocol `source-grouped-v2`, full model_leeching data; three separately
  seeded source-grouped splits (1, 20, 42) drawn from the same dataset.
- Same data splits, calibration and test windows, and references for the three
  methods within each run. Windows can overlap and are not independent.
- Fixed BGE-small encoder; learned kernel trained on 10% attack mixtures at
  training window 100 for 20 epochs, eight training windows per epoch, 32 fixed
  validation windows. Checkpoint chosen only by the validation objective.
- Test window sizes 250 and 500; attack ratios 5% and 10%. Each run uses 200
  benign calibration windows and 100 test windows per condition. Thresholds
  are each method's empirical 95th percentile on calibration windows.
- Full per-run rates and paths are in `outputs/known_pilot_v2/runs.csv`.

## Descriptive results

Mean across the three seeds, with the minimum and maximum seed in parentheses.
These ranges are not confidence intervals.

| Window | Method | FPR | TPR 5% | TPR 10% |
|---:|---|---:|---:|---:|
| 250 | RBF | 3.0% (0–8%) | 10.0% (3–18%) | 54.0% (36–74%) |
| 250 | Multi-RBF | 3.3% (0–9%) | 12.3% (4–22%) | 66.0% (48–83%) |
| 250 | Deep Kernel | 3.0% (0–9%) | 45.7% (25–63%) | 100% (100–100%) |
| 500 | RBF | 9.0% (2–22%) | 25.7% (5–65%) | 89.7% (80–100%) |
| 500 | Multi-RBF | 9.7% (1–25%) | 31.0% (8–77%) | 96.3% (91–100%) |
| 500 | Deep Kernel | 12.0% (0–34%) | 86.7% (68–100%) | 100% (100–100%) |

The learned kernel has a promising known-attack signal, but the FPRs are not
matched. In seed 42/window 500, FPR was 22%, 25%, and 34% respectively. A
diagnostic rerun saved calibration scores in
`outputs/known_pilot_calibration_audit_seed42_500/`: calibration rejected 5%
of its own windows for each method, while benign test rejection was much
higher. The benign test median score exceeded the calibration median for each
method. This demonstrates a score-distribution difference in that split, not
its cause; overlapping windows and source groups limit independent evidence.

The input format is a major limitation: all 10,062 attack rows begin with
`Given this context:` whereas none of the 10,062 benign rows do; average query
lengths are approximately 1,226 and 61 characters respectively. Learned
separation could exploit formatting, length, or task differences. There is no
unseen-attack test or controlled nuisance-feature ablation, and the training
objective is an exploratory proxy, not a validated power estimator. Do not use
these results to assert generalization, equal-FPR superiority, or significance.

Next investigate calibration/test distribution sensitivity using source-level
repeats, then test attack formats and length-controlled baselines or ablations.

## Follow-up diagnostics

A simple one-sided detector used the mean query character count in a window
minus the mean character count of its benign reference. Its threshold was the
95th percentile on the same 200 benign calibration windows; it used the exact
same reference and test draws as the MMD pilot. In all six settings it detected
100% of the 100 mixed windows at both 5% and 10% attack, with held-out FPR
between 0% and 11%. These figures are descriptive, not independent-window
confidence estimates. This does not establish what the deep network learned;
it does show that this dataset admits a very strong length-only signal.
Per-run results and source-split length statistics are in
`outputs/length_diagnostic/`.

All six configurations were rerun to save per-method calibration scores in
`outputs/calibration_diagnostic/`; descriptive thresholds, medians and FPRs
are collected in `calibration_summary.csv`. For seeds 1 and 20, benign test
medians were below calibration medians; for seed 42 they were above, for all
three methods at both window sizes. A source split or domain difference may be
involved, but the diagnosis does not establish the cause. Choosing thresholds
using test scores would invalidate the held-out evaluation. Further work must
examine source-aware calibration and uncertainty, and compare at independently
verified FPR using controlled traffic formats and unseen attacks.
