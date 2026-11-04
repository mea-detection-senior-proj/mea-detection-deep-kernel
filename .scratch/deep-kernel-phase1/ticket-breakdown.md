# Proposed Phase 1 Ticket Breakdown

Review state: awaiting user approval of granularity and blocking edges. These are draft slices, not published implementation tickets. The accepted Phase 1 specification remains unchanged.

Each implementation slice includes its own observable workflow verification and necessary numerical checks. Reuse existing orchestration, sampling, fitting, scoring, and reporting seams. No separate framework or speculative prefactoring ticket is justified; make any small preparatory change within the affected slice before extending its behavior. Phase 2 transfer, Phase 3 mixed training, and the dashboard are excluded.

## 01: Preserve upstream fixed-kernel baselines in reproducible runs

**What to build:** A researcher can run original RBF and Multi-RBF through the common workflow and obtain traceable results whose kernel/statistic behavior is verified against the retained upstream reference.

**Blocked by:** None (can start immediately).

- [ ] Preserve the original Gaussian kernel, benign median heuristic, Multi-RBF scales and equal weighting, bandwidth floor, degenerate behavior, unbiased MMD, and mean-reference score.
- [ ] Record the agreed upstream commit/blob identity and disclose the adapted evaluation protocol in saved evidence/reporting.
- [ ] Retain original source behavior without attack-informed fitting of either fixed baseline.
- [ ] A small complete baseline workflow generates reproducible scores and a report; meaningful numerical comparisons cover ordinary and edge inputs with declared float64 tolerances.
- [ ] Existing outputs and raw data are preserved, and baseline-only execution does not train a learned method.

## 02: Keep supported conditions when evaluation capacity is partial

**What to build:** A researcher can request the accepted grid, see unsupported conditions before expensive work, and still run supported mixed-traffic conditions when a large pure-attack window cannot be formed.

**Blocked by:** None (can start immediately).

- [ ] Capacity preflight, prepared protocols, execution, and report artifacts share an explicit supported/unavailable condition manifest with reasons.
- [ ] A pure-attack shortage does not remove valid mixtures; no query is duplicated within a window/reference draw to make a condition fit.
- [ ] Missing essential benign pools or fitting capacity fails clearly for the affected case/fit; numerical failures are not relabeled as capacity shortages.
- [ ] Availability is identical across compared methods and included in compatibility checks; unsupported, failed, and measured-zero conditions remain distinct.
- [ ] Dry-run fixture verification remains free of encoder/GPU allocation and output writes; a fixture with a supported mixture and unsupported pure window completes with explicit unavailable cells.

## 03: Compare an attack-informed learned-bandwidth RBF end to end

**What to build:** A researcher can select learned-bandwidth RBF alongside the existing methods, fit it on permitted pure pairs, and obtain calibrated scores, a replayable model, and report rows from the same workflow.

**Blocked by:** None (can start immediately).

- [ ] Extend method selection, validated configuration, capacity checks, fitting, persistence/reload, scoring, and reporting for this separately named control.
- [ ] Learn a single positive bandwidth with the accepted power objective, initialized from the permitted benign reference median; no neural feature map.
- [ ] Reuse permitted examples and paired RNG/sampling behavior with the pure deep-kernel comparator where applicable; apply the accepted optimizer budget and fixed validation policy.
- [ ] Select highest mean validation J, including epoch zero and earliest tie, then freeze before calibration/test.
- [ ] Save selected state, history, exposure/budget, timing, and protocol identity; replay produces the saved model's scores.
- [ ] A small complete comparison and independent numerical/gradient checks verify behavior without requiring real-data superiority or changing the original fixed baselines.

## 04: Compare a mean-window MLP classifier end to end

**What to build:** A researcher can select the MLP classifier alongside existing detectors and compare its benign-calibrated window decisions using the same frozen embeddings and held-out queries.

**Blocked by:** None (can start immediately).

- [ ] Extend selection, validated configuration, capacity checks, fitting, persistence/reload, scoring, and report rows through the existing workflow.
- [ ] Use the accepted feature trunk with a scalar logistic head and binary cross-entropy on logits, with the same permitted pure training examples and declared budget.
- [ ] Select lowest validation classification loss, including epoch zero and earliest tie, then freeze before calibration/test.
- [ ] Window scoring is the arithmetic mean of per-query sigmoid attack scores; benign reference draws do not affect this score and the outputs are not labeled calibrated malicious-intent probabilities.
- [ ] Save selected state, history, exposure/budget, timing, and protocol identity; replay produces matching public scores.
- [ ] A small complete comparison verifies finite bounded scores, mean aggregation, classifier-specific benign calibration, and test-independent model/threshold selection.

## 05: Produce the complete five-method query-efficiency comparison

**What to build:** A researcher can run all five methods on one shared protocol and receive complete per-seed tables, measured-FPR-aware minimum-window summaries, plots, and an English report.

**Blocked by:** 01: Preserve upstream fixed-kernel baselines in reproducible runs; 02: Keep supported conditions when evaluation capacity is partial; 03: Compare an attack-informed learned-bandwidth RBF end to end; 04: Compare a mean-window MLP classifier end to end.

- [ ] All five methods appear in outputs and reports, including shared available conditions and explicit unavailable reasons. Do not introduce another orchestration layer.
- [ ] Calibration scores exactly match each method's test statistic, using accepted reference/calibration/test counts, higher empirical quantiles, and strict alerts; thresholds never depend on the true attacker fraction.
- [ ] Compute per-dataset/seed/method/fraction minimum tested size with measured TPR >= 90% and measured FPR <= 5%; distinguish not reached, unavailable, failed, and zero detection.
- [ ] Report complete seed-level results and descriptive means/sample SD with measured FPR beside TPR; preserve dataset identity and all declared inference limits.
- [ ] Produce window-size and attacker-fraction plots, replayable per-window records, compatible-protocol provenance, and training/evaluation cost summaries.
- [ ] A complete five-method fixture workflow covers exact endpoint boundaries, excessive FPR, partial capacity, no qualifying size, all unavailable sizes, protocol mismatch, checkpoint replay, no overwrite, and retained failure states.

## 06: Complete the model_leeching Phase 1 benchmark

**What to build:** A researcher receives the complete three-seed five-method result set for model_leeching on the accepted grid, with context-group provenance and checked report artifacts.

**Blocked by:** 05: Produce the complete five-method query-efficiency comparison.

- [ ] Audit capacity/grouping and preserve source hashes; freeze the accepted configuration and shared draws before fitting/scoring.
- [ ] Run seeds 1/20/42, windows 100/200/500/1500, benign-only and 1/5/10/25/100% attacks on supported conditions, with frozen embeddings and pure training.
- [ ] Complete supported cells, diagnose execution failures rather than hiding/replacing them, and retain explicit capacity-unavailable cells.
- [ ] Deliver complete compatible artifacts, histories/checkpoints, per-seed measured TPR/FPR, endpoint summaries, plots, and an English dataset report.
- [ ] Reconstruct sampled decisions/rates from saved scores and thresholds, verify paired draws and raw-data preservation, and label prior inspected data exposure and earlier protocol results honestly.

## 07: Complete the Meaeq_SST-2 Phase 1 benchmark

**What to build:** A researcher receives the complete five-method three-seed MeaeQ benchmark, including valid mixed-traffic results and visible large-window pure-attack capacity limits.

**Blocked by:** 05: Produce the complete five-method query-efficiency comparison.

- [ ] Re-audit the accepted grid and fitting capacity before expensive work; record grouping/provenance limits and unchanged raw hashes.
- [ ] Run the accepted seeds, window sizes, and fractions with pure training, shared draws, and calibration-only thresholds.
- [ ] Retain supported mixed conditions when pure windows are unsupported; show actual counts, availability reasons, and no duplicated queries within draws.
- [ ] Complete supported cells and diagnose execution failures without omitting seeds or changing settings based on test outcomes.
- [ ] Deliver compatible per-window evidence, checkpoints/histories, rates, endpoints, plots, timing, and an English report with reconstruction checks and SST-2 overlap disclosure.

## 08: Complete the ME_BERT_sst2_wiki Phase 1 benchmark

**What to build:** A researcher receives the complete five-method three-seed BERT-WIKI benchmark as a separate dataset fit, with reproducible evidence and its limits disclosed.

**Blocked by:** 05: Produce the complete five-method query-efficiency comparison.

- [ ] Audit grouping/capacity, preserve raw hashes, and freeze the accepted protocol before the run.
- [ ] Run the accepted seeds, window sizes, benign-only and attack fractions with pure training and one frozen instance per dataset/seed/method.
- [ ] Complete supported conditions with shared evaluation draws, diagnose execution failures, and preserve all seeds and explicit availability states.
- [ ] Deliver compatible scores/thresholds, checkpoints/histories, cost records, per-seed rates, endpoints, plots, and an English report with sampled reconstruction checks.
- [ ] Keep this fit separate from MeaeQ and disclose shared benign texts rather than treating the datasets as independent replications.

## 09: Publish the Phase 1 evidence and findings

**What to build:** A researcher receives one auditable English Phase 1 findings report that connects the three completed dataset comparisons to the agreed contribution and identifies what remains for later phases.

**Blocked by:** 06: Complete the model_leeching Phase 1 benchmark; 07: Complete the Meaeq_SST-2 Phase 1 benchmark; 08: Complete the ME_BERT_sst2_wiki Phase 1 benchmark.

- [ ] Reconcile coverage, protocol identities, method/seed completeness, unsupported cells, and supporting artifacts before declaring the Phase 1 comparison complete.
- [ ] Present dataset-separated detection/window/fraction results, measured FPR, per-seed minimum effective windows, descriptive variability, and training/evaluation costs with traceable evidence.
- [ ] Explain gains, failures, and non-crossings without claiming matched FPR when only calibration targets match, extrapolating minima, hiding adverse seeds, or pooling dependent datasets into independent evidence.
- [ ] Distinguish original-baseline adaptation, richer kernel learning, and direct classification; do not attribute every difference solely to the neural map or objective.
- [ ] State development-data exposure, finite-pool uncertainty limits, capacity/source limitations, and the absence of Phase 2 generalization evidence and Phase 3 mixed-training results.
- [ ] Preserve negative/mixed outcomes as valid findings; deliver the checked report and plots before dashboard work, without implementing later phases.

## Dependency Summary

- Initial frontier: 01, 02, 03, 04.
- 05 requires all four capabilities for a complete faithful five-method comparison.
- 06, 07, and 08 require 05 and are otherwise independent dataset runs; execute according to available compute resources.
- 09 requires all three dataset result sets.
- Shared implementation surfaces may require coordinated or sequential edits, but they are not artificial scientific blocking edges.
- Every slice owns its verification. There is no separate horizontal test-only, configuration-only, or scaffolding ticket.
