# Phase 1: Deep-Kernel MMD for Low-Query Model Extraction Detection

Status: ready-for-agent

Scientific scope and numerical defaults accepted on 2026-11-04. Mixed-traffic training is deferred to Phase 3. This specification describes work to be done, not completed implementation or new experimental results.

## Problem Statement

The researcher wants to contribute a learned deep kernel to an existing MMD detector for model extraction traffic. The intended benefit is stronger detection when attacker queries form a small fraction of a detection window, and a smaller minimum effective window size under a false-positive budget.

The repository contains the original fixed-kernel detector, an exploratory Pilot, and a newer config-driven workflow. Their kernels, training objectives, data partitions, calibration rules, and evaluation grids are not interchangeable. Previously inspected results do not establish superiority at comparable measured FPR: some measured FPRs exceed the nominal calibration target, and reusing development-exposed data cannot establish untouched confirmation.

The researcher needs a coherent first comparison that preserves the original RBF and Multi-RBF methods, includes attack-informed controls, tests low-query and low-ratio conditions separately, and reports negative or unsupported results honestly. Pure-attack training must remain distinct from mixed-traffic evaluation, while later generalization and mixed-training work stays outside the first implementation milestone.

## Solution

Extend the existing experimental workflow to compare five methods on shared, reproducible windows: original RBF MMD, original Multi-RBF MMD, attack-informed learned-bandwidth RBF MMD, an MLP classifier, and pure-trained deep-kernel MMD.

Start with the three local original-benchmark datasets. Fit learned methods separately for each dataset and seed, use a shared frozen sentence encoder, choose checkpoints from validation, calibrate thresholds from benign traffic, and evaluate every method on the same held-out windows. Reuse each fitted detector across all supported window sizes and attacker fractions.

Deliver per-window records, complete per-seed tables, plots, and an English report. Define minimum effective window size as the smallest tested supported size with measured TPR at least 90% and measured FPR at most 5%, separately per dataset, seed, method, and attacker fraction. Preserve unavailable conditions and failure to reach the endpoint.

Phase 1 is a descriptive known-attack benchmark. Phase 2 addresses attack-family and generator transfer. Phase 3 retains the planned mixed-training ablation. Build the offline dashboard after checking the primary experimental outputs.

## User Stories

1. As a researcher, I want the contribution framed as an adaptation and empirical evaluation, so that its novelty is described accurately.
2. As a researcher, I want window size and attacker fraction treated separately, so that query efficiency and dilution are not confused.
3. As a researcher, I want to start with the three available original-benchmark datasets, so that Phase 1 has a manageable scope.
4. As a researcher, I want each dataset trained and evaluated separately, so that pooled-domain learning does not confound the first comparison.
5. As a researcher, I want known attack examples allowed during learned-method fitting, so that the detector can learn relevant differences.
6. As a researcher, I want evaluation queries held out from fitting and model selection, so that results extend beyond training queries.
7. As a researcher, I want all methods to use the same frozen sentence embeddings, so that encoder changes do not confound the comparison.
8. As a researcher, I want the original RBF method extracted faithfully, so that it remains a valid source baseline.
9. As a researcher, I want original Multi-RBF scales and equal weighting preserved, so that a redesigned method is not called the original baseline.
10. As a reviewer, I want upstream provenance and numerical verification recorded, so that I can assess baseline fidelity.
11. As a researcher, I want learned-bandwidth RBF as a separate control, so that I can compare the deep construction with simpler attack-informed kernel learning.
12. As a researcher, I want an MLP classifier trained on the same permitted examples, so that I can compare MMD with direct supervised classification.
13. As a researcher, I want classifier scores averaged over each window, so that the classifier uses the same detection unit.
14. As a researcher, I want the deep kernel and objective to follow Liu et al.'s starting method, so that deviations are explicit.
15. As a researcher, I want pure-attack training in Phase 1, so that the first result set evaluates the agreed starting method.
16. As a researcher, I want mixed-traffic evaluation in Phase 1, so that postponing mixed training does not remove the low-ratio question.
17. As a researcher, I want mixed training retained for Phase 3, so that it does not expand the first implementation milestone.
18. As a researcher, I want checkpoint selection based on validation, so that test performance does not choose the trained version.
19. As a researcher, I want every selected method tested, so that checkpoint selection does not remove methods from the comparison.
20. As a researcher, I want selected parameters frozen before calibration and testing, so that scoring cannot change the learned detector.
21. As a researcher, I want one fitted instance per dataset and seed reused across conditions, so that the detector does not require the true attacker fraction.
22. As a researcher, I want exact integer attacker counts in the primary grid, so that fractions stay comparable across window sizes.
23. As a researcher, I want results at 1%, 5%, and 10%, so that difficult dilution conditions are mandatory reporting rather than optional successes.
24. As a researcher, I want 25% and pure-attack conditions as reference points, so that I can observe behavior as the attack signal strengthens.
25. As a researcher, I want benign-only windows for every method, so that measured FPR accompanies attack TPR.
26. As a researcher, I want capacity checked before embedding and training, so that impossible conditions are identified before expensive work.
27. As a researcher, I want supported mixed conditions retained when a pure window is too large, so that one unavailable cell does not erase valid evidence.
28. As a reviewer, I want unavailable cells and reasons shown, so that missing evidence is not silently omitted or mistaken for zero detection.
29. As a researcher, I want distinct queries inside each draw, so that duplication does not manufacture supported conditions.
30. As a researcher, I want shared calibration/test windows and applicable reference draws, so that method differences are paired fairly.
31. As a researcher, I want protocol and draw identities verified on reuse, so that incompatible runs cannot be combined.
32. As a researcher, I want thresholds set using benign calibration only, so that attack labels do not determine the operating threshold.
33. As a researcher, I want calibration and testing to compute the same score, so that a threshold is applied to its intended statistic.
34. As a researcher, I want thresholds independent of the true attacker fraction, so that evaluation respects available detection-time information.
35. As a reviewer, I want calibration target FPR distinguished from measured FPR, so that nominal settings are not presented as demonstrated control.
36. As a researcher, I want high-TPR results with excessive FPR excluded from endpoint success, so that false alarms cannot purchase a misleading advantage.
37. As a researcher, I want minimum effective window size calculated only from tested sizes, so that an unmeasured minimum is not inferred.
38. As a researcher, I want an explicit not-reached result, so that negative results remain visible.
39. As a researcher, I want every seed reported, so that favorable seeds do not replace the full experiment.
40. As a reviewer, I want per-seed results beside descriptive summaries, so that variability remains visible.
41. As a reviewer, I want three-seed standard deviation labeled correctly, so that it is not mistaken for a confidence interval.
42. As a reviewer, I want finite-pool simulation precision distinguished from population uncertainty, so that repeated draws are not called independent new traffic.
43. As a researcher, I want group-aware partitions and duplicate auditing, so that documented sources and texts do not cross train/test purposes within a fit.
44. As a reviewer, I want shared benign texts between the SST-2 datasets disclosed, so that their results are not treated as independent replications.
45. As a researcher, I want raw data preserved and transformations hashed, so that provenance remains auditable.
46. As a researcher, I want random streams separated by experimental stage, so that changing training does not silently change test draws.
47. As a researcher, I want learned controls given the same permitted examples and declared budget, so that they are not deliberately disadvantaged.
48. As a reviewer, I want training and evaluation costs recorded, so that performance benefits can be assessed alongside cost.
49. As a researcher, I want saved checkpoints and histories, so that selected models can be replayed and inspected.
50. As a researcher, I want per-window scores, thresholds, and decisions, so that summary rates can be reconstructed.
51. As a researcher, I want reports to include all five methods, so that a new method is not silently omitted by reporting code.
52. As a researcher, I want incomplete and incompatible runs rejected by reporting, so that misleading aggregates cannot be produced.
53. As a researcher, I want new runs to use new output destinations, so that earlier evidence cannot be overwritten accidentally.
54. As a researcher, I want failures recorded without silently replacing seeds or settings, so that numerical problems remain visible.
55. As a researcher, I want old Pilot and window-250 results labeled separately, so that different protocols are not merged.
56. As a researcher, I want reproducible tables, plots, and an English report before the dashboard, so that presentation rests on checked evidence.
57. As a researcher, I want transfer evaluation deferred to Phase 2, so that Phase 1 stays focused on its accepted benchmark.
58. As a researcher, I want future held-out attack conditions protected from earlier selection, so that later generalization claims have a clear meaning.

## Implementation Decisions

### Existing modules and comparison scope

- Extend the existing configuration/CLI, experiment workflow, capacity preflight, locked-protocol preparation, detector scoring, calibration/evaluation, and comparison-report modules. Reuse the current workflow and scoring interface rather than creating another framework or orchestration layer.
- Add learned-bandwidth RBF and classifier support consistently through selection, validation, capacity checking, fitting, checkpoint persistence/reload, evaluation, and reporting. The current main pipeline supports only the original two fixed kernels and pure-trained deep-kernel MMD.
- Replace whole-run rejection for an isolated unsupported evaluation condition with explicit condition availability. Retain supported conditions, show unavailable reasons, and require identical supported-cell coverage across compared methods. Missing essential reference/calibration pools or training/validation capacity remains an actionable failure for the affected case or fit.
- Extend the current report beyond its three hardcoded method names to include all five methods, endpoint summaries, and plots. Preserve lock, draw, completion, duplicate-result, and condition-coverage checks.
- Keep the complete original detector available as a reference. Label the common evaluation as adapted; it is not unchanged reproduction of the original full protocol. Keep the retained Pilot's different method and artifacts separate.

### Accepted experimental matrix

- Datasets: `model_leeching`, `Meaeq_SST-2`, and `ME_BERT_sst2_wiki`, fitted independently. One learned instance per method/dataset/seed is reused across all supported evaluation conditions; no pooled training in Phase 1.
- Seeds: 1, 20, 42. Window sizes: 100, 200, 500, 1,500. Attacker fractions: 1%, 5%, 10%, 25%, 100%, plus benign-only. These sizes yield exact integer counts; record actual counts and fractions regardless.
- Main learned-method training is pure: 100 benign queries versus 100 known attack queries per kernel pair. Give the classifier the same permitted 100 benign and 100 attack examples per paired training batch.
- Mixed-traffic evaluation remains mandatory. Mixed-training implementation and execution belong to Phase 3; do not build an unused mixed-training mode as part of Phase 1.

### Encoder and original baselines

- Use the locally pinned BAAI/bge-small-en-v1.5 encoder with normalized embeddings, frozen for every method. Record encoder content identity and embedding-generation dtype separately from float64 detector/training arithmetic.
- Preserve the upstream Gaussian RBF formula, positive-distance median-bandwidth heuristic, degenerate fallback, bandwidth floor, unbiased MMD estimator, and reference-averaged score. Multi-RBF equally averages scales 0.5, 1, 2, and 4 around the same benign reference median. Neither original baseline learns from attack examples.
- Provenance: upstream commit 7532c25b973ef13f3f971e73a40ff46d469e3fea and retained detector Git blob 25844d41a113dfc520c4fbcb136afda82babc841. Verify extraction including edge behavior. Optimized reduction order may change floating-point results; use declared tolerances rather than claiming bitwise identity.
- Initialize the learned-bandwidth RBF and deep base kernel from the same permitted benign reference median. The shallow control learns one positive Gaussian bandwidth using the power objective and has no neural feature map.

### Deep kernel, objective, and classifier

- Use a feature map from 384 to 128, ReLU, then 64 outputs. Multiply the original-embedding Gaussian kernel by a mixture of the learned-feature Gaussian kernel with a constant residual. The learned-feature weight is one minus epsilon; the residual weight is epsilon. Learn both positive bandwidths with exponential parameterization and epsilon with sigmoid parameterization, initially 0.1.
- Initialize feature bandwidth from mapped benign training embeddings only. The original-space component concerns frozen embeddings and cannot recover distinctions the encoder discarded.
- For learned kernels, maximize Liu et al.'s paired unbiased squared-MMD numerator divided by the square root of its regularized asymptotic variance estimate. The pairwise matrix adds the two within-group kernels and subtracts the two cross-group kernels. Exclude its diagonal in the numerator; retain the full matrix for four times the population variance of row means. Add regularizer 1e-8 before the square root.
- This variance is not variability across traffic-window scores. The power criterion is asymptotically motivated and does not guarantee small-window superiority. Evaluation uses the upstream all-cross unbiased MMD estimator for every MMD method; finite-sample values need not equal the paired training estimator.
- The classifier uses the same feature-map trunk plus a scalar logistic head. Train with binary cross-entropy on logits. Average per-query sigmoid attack scores for the window score, with no reference comparison in the classifier score. These outputs are not assumed calibrated probabilities of malicious intent. Reuse the existing scoring interface.
- Deep versus fixed kernels measures the full attack-informed approach. Deep versus learned-bandwidth RBF compares a richer kernel construction beyond bandwidth learning, not the neural map alone, because composition and parameterization also change. Deep versus classifier compares learned approaches, not the loss alone independently of scoring.

### Fitting and checkpoint selection

- Use Adam, learning rate 0.001, weight decay 0.0001, gradient norm clip 10, and at most 30 epochs with 16 optimizer steps each. Freeze the declared settings before the planned comparison; no large hyperparameter search is required.
- Use 32 fixed pure validation pairs. Maximize mean validation J for learned kernels and minimize mean validation classification loss for the classifier. Include epoch zero and retain the earliest candidate on ties. Fixed baselines have no learned checkpoint.
- Share permitted examples and paired training/validation draws across learned controls where applicable. Equal optimizer-step budgets do not mean equal compute or optimization difficulty; record training/evaluation costs.
- Fit using training/validation inputs only. Freeze selected parameters before calibration/test. No test-based checkpoint, hyperparameter, seed, or variant selection; every method still enters the final comparison.
- Record numerical failures without silently changing settings, omitting seeds, or replacing them with favorable runs.

### Data and protocol artifacts

- Keep the existing 20/10/25/20/25 percent group allocation to train, validation, benign reference, benign calibration, and test. Group allocations do not guarantee equal row proportions.
- Retain documented ID, normalized-text, transitive source/context grouping, cross-label ambiguity handling, and duplicate policy. Preserve raw files and record hashes and transformations. Exact-text grouping and synthetic IDs do not establish independent users, campaigns, or semantic sources.
- Keep purposes disjoint within each fit. Disclose the 9,629 benign normalized texts shared between the SST-2 datasets; their separate fits are not independent dataset replications. Joint grouping/decontamination is required before future pooled or cross-dataset work, not pooled learning in Phase 1.
- Audit capacity for the accepted grid before expensive work. MeaeQ has too few held-out attacks for some large pure windows. Do not duplicate queries within a window or reference draw to make a cell fit. Different draws may reuse queries.
- Prepare shared evaluation windows and applicable reference draws before comparison. Separate initialization/training, validation, calibration, and test RNG streams. Record data, encoder, split, pool, code, configuration, and draw identities.
- Locks prove artifact consistency, not access control or untouched data. Separately run methods may be combined only with matching relevant locks/draws, supported cells, and condition coverage.
- Reuse artifact conventions, extending them only for needed method identity, availability/reason, scores, thresholds, decisions, fitted parameters, checkpoint selection/history, and timing. Keep dataset identity in aggregation keys or separate reports; do not silently pool benchmarks.

### Calibration, endpoint, and reporting

- Use 20 benign reference draws per MMD window, each the incoming window size; 500 benign calibration windows; and 200 test windows per supported condition. Share calibration/test windows and reference draws across applicable methods. These are resampled windows, not independent new traffic units.
- Calibrate the actual test score: mean-reference MMD for kernels and mean query score for the classifier. Use a method-specific empirical 95th-percentile threshold with higher interpolation and strict score-greater-than-threshold alerts.
- Thresholds may depend on dataset, seed, method, and window size, not the true attacker fraction. Lock before testing. Show measured benign FPR with each attack TPR and use same nominal calibration target when actual FPR differs.
- Minimum effective window size is calculated per dataset, seed, method, and attacker fraction from tested supported sizes only. Inclusive requirements are measured TPR at least 90% and measured FPR at most 5%. High TPR with excessive FPR does not qualify.
- Report not reached within the evaluated grid when supported sizes exist but none qualifies. Report unavailable when none is supported. Keep unsupported cells, numerical failures, and measured zero detection distinct.
- Report every seed, descriptive means and sample SD, and per-seed endpoints. SD is not a confidence interval; an empirical crossing is not population-level FPR control. No interpolation to an untested minimum.
- Formal significance and population confidence intervals are not Phase 1 requirements. Any optional conditional Monte Carlo interval must identify its fixed pools, fitted detector, threshold, sampler, and independent RNG draws; it cannot represent new-user or source-population uncertainty.
- Retrospective ROC/AUROC may be secondary descriptive analysis. Test-derived thresholds cannot replace calibration thresholds or establish the prespecified endpoint.
- Deliver per-window scores/decisions, calibration scores/thresholds, provenance/configuration records, availability manifests, checkpoints/histories, full tables, plots, empirical minimum-window summaries, and an English findings/limitations report. Plot detection against window size and attacker fraction with measured FPR available alongside it.
- Write to new output destinations and reject overwrites. Preserve running/complete/failed states. Incomplete or incompatible artifacts cannot yield a completed comparison. Keep old Pilot and window-250 evidence separate.

## Testing Decisions

- **Primary existing seam:** exercise the complete configured experiment workflow, from validation/capacity preflight through shared protocol preparation, fitting, calibration, evaluation, and generated report artifacts. Use small synthetic datasets and deterministic fixture embeddings, replacing only the external encoder. Keep actual splitting, sampling, fitting, scoring, thresholding, and reporting. No new orchestration seam is needed.
- **Good tests:** assert observable outputs, errors, persistence, reproducibility, numerical invariants, and report semantics. Avoid private call-order assertions, implementation-mirroring expected results, and tests requiring real-data superiority. Use small fixture budgets for automation and check production defaults through resolved configuration.
- **Prior art:** existing experiment CLI tests already cover complete selected-method workflows with fixture embeddings, reports/checkpoints, dry runs, lock reuse/conflicts, no overwrite, and failure records. Existing locked-run tests cover shared draws, tampering, incompatible runs, and checkpoint replay. Extend these patterns for five methods and explicit availability.
- **Pipeline acceptance:** a fixture run includes all five methods in score artifacts and reports and persists every learned method's selected model. Dataset fits stay separate. Same-settings reruns reproduce deterministic scientific outputs, excluding inherently variable timing/status timestamps.
- **Capacity acceptance:** a fixture with enough attacks for a mixture but not a pure window retains the mixture and emits unavailable reasons consistently for all methods. Missing essential benign pools or training/validation capacity fails clearly before expensive work. Dry runs load no encoder, allocate no GPU, and write no run artifacts.
- **Protocol integrity:** matching locks/draws and supported conditions are checked across methods; changed hashes, incompatible settings, incomplete runs, duplicate results, or inconsistent method coverage cannot produce a completed comparison.
- **Necessary existing numerical seams:** retain scalar-reference and original-detector comparisons for RBF/Multi-RBF, MMD, and mean-reference scoring. Add original bandwidth-floor and degenerate-input coverage. Bound optimized float64 differences with stated tolerances.
- **Deep-kernel prior art:** reuse existing independent scalar kernel/variance formulas, positive-semidefinite fixture checks, finite-difference/autograd comparisons, checkpoint selection, freezing, and replay tests. Extend the public mathematical behavior checks to learned-bandwidth RBF; no separate training test framework is required.
- **Learned behavior:** verify finite outputs/gradients, positive bandwidths, epoch-zero/tie handling, validation-only selection, frozen replayable parameters, and saved metadata. Check finite bounded classifier scores, mean-query window scoring, and invariance to unused reference draws.
- **Calibration behavior:** known fixture scores establish the higher quantile, strict threshold boundary, and consistent calibration/test statistic. Changing only held-out test observations must not change a selected checkpoint or calibrated threshold. Assert artifacts and scores rather than private signatures.
- **Endpoint behavior:** fixture rates cover exact 90%/5% boundaries, excessive FPR despite high TPR, a smaller qualifying size, unsupported sizes, zero TPR, no qualifying size, and no supported sizes. Check per-seed endpoints and dataset-separated summaries against these fixtures.
- **Report behavior:** include all selected methods, seeds, and supported cells; unavailable reasons; reconstructible rates; complete artifacts; and failure records. Check plots and tables cover the declared matrix and descriptive variation is not labeled confidence or a population guarantee.
- **Data prior art:** reuse existing transitive-group, context-disjointness, duplicate-accounting, exact-count, no-replacement, and readiness-capacity tests. Re-audit the accepted grid. Tests establish the documented policy, not unverified user/campaign independence.
- Authoring this spec does not execute acceptance tests or the scientific benchmark. Real-data superiority is an experimental outcome, not an automated correctness requirement.

## Out of Scope

- Phase 2 unseen-family, unseen-generator, pooled-training, or cross-dataset experiments and their exact dataset selection.
- Phase 3 mixed-training implementation/execution or unused training-mode scaffolding added in advance.
- All fourteen original benchmark pairs in the first comparison.
- Sentence-encoder fine-tuning, large architecture searches, and large hyperparameter sweeps.
- New kernel theory, guaranteed superiority, or reaching the endpoint in every condition.
- Claiming comparisons isolate only the neural feature map or only the classifier loss.
- Replacing original fixed baselines with attack-informed variants, or calling the adapted protocol unchanged reproduction.
- Merging old Pilot/window-250 artifacts into the new protocol.
- Test-based tuning, threshold adjustment, favorable-seed selection, true-attacker-fraction model selection, or duplicated queries to manufacture capacity.
- Population-level FPR guarantees, formal significance claims, independent-user/campaign claims, sequential/streamwise guarantees, and real-time latency claims.
- Production security infrastructure, attribution/proof of malicious intent, prevention guarantees, victim-LLM training, unauthorized extraction, or multimodal attacks.
- Dashboard implementation as a prerequisite for the main comparison; the overall offline demonstration remains later work.

## Further Notes

- Negative or mixed findings remain valid outcomes. The contribution is reproducible evidence about the effectiveness, limits, and costs of this adaptation.
- The current main workflow lacks the two additional learned controls. Legacy Pilot mixed training uses fixed 10% mixtures and an across-window proxy; it is not the planned Liu-objective ablation.
- All three datasets have inspected prior results. A reshuffle does not create untouched confirmation. Reasons for earlier elevated FPR and source independence remain unverified; this spec makes no causal diagnosis.
- Roadmap: Phase 1 pure-trained benchmark, Phase 2 transfer, Phase 3 training-distribution ablation. Medical and SST-2 RANDOM were candidates, not selected requirements. Reserve future attack holdouts before earlier fitting or method selection.
- Retain the Phase 3 outline without implementing it: one mixed-trained kernel per dataset/seed; window 100; equally sampled 1/5/10/25% fractions; disjoint benign comparison/incoming subsets within a pair; frozen encoder; unchanged kernel/objective; matched pair size and optimizer-step budget; explicit attack exposure; 32 fixed validation pairs, eight per fraction, selected by equally weighted mean validation J; paired evaluation with variant-specific calibration. Review data exposure and freeze that later protocol before using results for selection.
- [Original proposal](../../FIRSTDRAFT.md)
- [Project glossary](../../GLOSSARY.md)
- [Accepted research and phase decisions](../../docs/adr/0001-query-efficiency-and-unseen-attack-evaluation.md)
- [Baseline preservation and provenance](../../docs/adr/0002-preserve-upstream-fixed-kernel-baselines.md)
- [Local readiness evidence](../../docs/DATA_READINESS_TH.md)
- [Original MMD detector paper](https://arxiv.org/html/2606.05725v1)
- [Liu et al., Learning Deep Kernels for Non-Parametric Two-Sample Tests](https://proceedings.mlr.press/v119/liu20m/liu20m.pdf)
