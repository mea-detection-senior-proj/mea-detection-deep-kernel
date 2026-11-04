---
status: accepted
---

# Evaluate query efficiency with a reusable attack-informed kernel

The primary research question is whether deep-kernel MMD reaches a target detection rate with a smaller window than conventional MMD at a given attacker fraction and controlled false-positive budget. Training may use known attack examples over frozen sentence embeddings; each training fold produces one frozen kernel reused across evaluated window sizes and attacker fractions, rather than a kernel specialized to the true incoming attacker fraction. For unseen-attack evaluation, historical benign traffic from the monitored service is permitted with purpose-separated partitions, while the held-out attack family is excluded from kernel training, parameter tuning, and method selection.

## Methodological starting point

Use a faithful adaptation of Liu et al. (2020)'s kernel and variance-normalized training objective as the primary starting point. Any methodological modifications must be identified and evaluated separately.

## Training-distribution comparison

Interview Q12 accepted pure-attack training as the primary starting point: compare benign samples with pure known-attack samples during power-oriented kernel learning. Add mixed-traffic training as an explicitly separate ablation to investigate the effect of changing the training distribution. Each variant produces one frozen kernel per training fold and seed, reused across evaluation window sizes and attacker fractions; the true incoming attacker fraction must not select the deployed variant.

Interview Q22 accepted a design for one mixed-trained deep kernel per dataset and seed, with training-window size 100 and attacker fractions 1%, 5%, 10%, and 25% selected with equal probability across training pairs. Keep the sentence encoder frozen. Match pure and mixed variants by pair size and optimizer-step budget, and report actual benign/attack exposure because the number of attack queries per pair differs by design. In the Q24 shared-understanding review, the user moved this ablation to Phase 3. Retain its design without making its implementation or execution part of Phase 1; it is not an additional primary comparator or a test-dependent replacement for the pure-trained kernel. Phase 3 comparisons should use paired evaluation windows under a protocol fixed before their results are used for selection, and must identify any previously exposed evaluation data.

Interview Q21 accepted objective-based within-method checkpoint selection before calibration/test: maximize validation J for the deep kernel and learned-bandwidth RBF, and minimize validation classification loss for the MLP classifier. All five methods still undergo the final comparison. Start from a small architecture and a declared training budget rather than making a large hyperparameter search a Phase 1 requirement.

## Consequences

Thresholds may depend on the known window size and chosen false-positive budget, but the detector must not require the true attacker fraction. Query efficiency is measured separately at different attacker fractions; a higher detection rate at one fixed window size is supporting evidence rather than sufficient evidence of a smaller required window. Unseen-attack results do not establish transfer to an unfamiliar benign service or domain.

## Comparison methods

Interview Q6 was accepted: compare the proposed deep-kernel MMD with upstream fixed RBF MMD, upstream fixed Multi-RBF MMD, an attack-informed RBF with learned bandwidth, and an MLP classifier on the shared frozen embeddings. The learned controls receive the same permitted training examples. The two upstream fixed baselines must retain their original method identity; the learned-bandwidth RBF is a separately named control, not a replacement for either original baseline.

Interview Q13 accepted the mean of per-query attack scores as the classifier's primary window score. Select its method-specific threshold using benign calibration windows. These classifier scores are not assumed to be calibrated probabilities of malicious intent. Alternative aggregation rules require separately identified experiments and must not be chosen from final test results.

## Query-efficiency endpoint

Interview Q11 accepted reporting full performance tables and curves together with a prespecified endpoint: the smallest evaluated window size reaching TPR >= 90% under the FPR <= 5% requirement, separately at each attacker fraction. If no tested window reaches the endpoint, report it as not reached within the evaluated grid; do not extrapolate to an untested size. Fix this criterion before the planned evaluation and do not adjust thresholds from test outcomes to make a method pass. The Phase 1 interpretation is the empirical endpoint described below; nominal calibration at 5% alone does not demonstrate held-out FPR control.

## Phase 1 evidence and repeatability

Interview Q19 accepted Phase 1 as a descriptive empirical benchmark on the evaluated datasets. Set method-specific thresholds using benign calibration with a nominal 5% FPR target, freeze them before testing, and always report measured test FPR beside TPR. A condition whose measured FPR exceeds 5% does not meet the empirical query-efficiency endpoint, even if TPR exceeds 90%. Passing the empirical endpoint is not a population-level FPR guarantee or a declaration that confidence bounds meet the same targets.

Repeated window draws improve precision for the fixed finite-pool sampling procedure; they do not add independent source traffic. If conditional Monte Carlo intervals are reported, identify that estimand and verify independent random draws conditional on the fitted model, threshold, and fixed pools. Do not present them as uncertainty for new users, campaigns, or source populations. No population-level guarantee is accepted for Phase 1.

Interview Q20 accepted seeds 1, 20, and 42. Within each dataset and seed, use shared partitions and test windows across methods. Report each seed, descriptive mean and standard deviation, and per-seed empirical minimum effective window sizes or failure to reach the endpoint. Three-seed standard deviation is not a confidence interval, and favorable seeds must not replace complete reporting.

## Evaluation scope

Interview Q14 accepted considering additional datasets from the original authors' sources to establish an appropriate final evaluation. Existing local results remain useful for development, but a new split or new resampled windows alone must not be described as independent confirmation. Dataset selection requires checking provenance, cross-dataset grouping, and whether the held-out condition represents a new attack family, a within-family generator or adaptive variant, a domain change, or a combination of these.

Interview Q15 accepted reporting requested attacker fractions 1%, 5%, 10%, 25%, and 100%, with particular emphasis on 10% and below. The 1% condition is part of the main reporting scope rather than an optional success-only result; reaching the 90% detection target is not required for every condition. Include benign-only windows for FPR evaluation. Report actual attacker counts and fractions, and mark unsupported cells instead of duplicating queries within a window to fill them.

Interview Q16 accepted primary window sizes 100, 200, 500, and 1,500. Each primary window size represents every requested attacker fraction exactly with an integer attacker count. Existing window-250 results remain identified as earlier exploratory results rather than being silently combined with the new primary grid.

## Phased evaluation

The user chose to begin with the benchmark setting from the original MMD study. Phase 1 compares the five agreed methods on original-benchmark data in a known-attack setting, with pure-attack training for the learned comparison methods, distinct training and evaluation queries, preserved upstream fixed-baseline computation, and the accepted common evaluation protocol and grids. Phase 1 still evaluates mixed-traffic windows at 1%, 5%, 10%, and 25%, as well as pure-attack and benign-only windows. Deferring mixed training does not defer mixed-traffic evaluation. This is an adapted comparison rather than an assertion of exact reproduction of the original paper's full protocol.

Interview Q17 accepted starting Phase 1 with the three available local datasets: `model_leeching`, `Meaeq_SST-2`, and `ME_BERT_sst2_wiki`. Broader coverage of the original fourteen dataset pairs is a possible later expansion, not a requirement for this first comparison. These three datasets are development-exposed benchmarks; their prior pilot results must be acknowledged rather than treating a reshuffle of the same data as untouched confirmation.

Interview Q18 accepted separate training and evaluation for each Phase 1 dataset, rather than pooled training across datasets. Fit the deep kernel, learned-bandwidth RBF, and MLP classifier using that dataset's permitted training and validation partitions; use the corresponding held-out test partition for evaluation. Each fitted instance is reused across all supported window sizes and attacker fractions in that dataset. The original fixed baselines use dataset-specific benign reference traffic and their preserved bandwidth-selection rules. Phase 1 therefore evaluates dataset-specific known-attack detectors and does not establish that one shared detector works across datasets.

Phase 2 addresses attack-family and generator transfer. Its specific datasets are not yet selected; the proposed medical and RANDOM datasets remain candidates rather than accepted requirements. To support a genuinely held-out claim, reserve the relevant attack families or conditions before they influence Phase 1 method selection; postponing their evaluation alone does not make previously used conditions unseen. Generalization remains part of the overall project objective, with its execution deferred.

Phase 3 addresses the planned mixed-training ablation. The user explicitly chose this sequence in the Q24 review: establish the pure-trained benchmark first, evaluate transfer in Phase 2, then investigate changing the training distribution in Phase 3. Later phases require their own execution-level data and protocol review.

## Deliverable sequencing

Interview Q23 accepted prioritizing a reproducible experimental pipeline, per-window scores and decisions, complete TPR/FPR tables, comparison plots, per-seed minimum effective window summaries, and provenance/configuration records. Build the offline dashboard or demonstration after the primary experimental outputs have been checked. The demonstration remains an overall project deliverable rather than a prerequisite for producing the main comparison.

## Review and deferred decisions

The user confirmed shared understanding and the numerical defaults in Q24 on 2026-11-04, with the amendment that mixed training moves to Phase 3. The consolidated [Phase 1 specification](../../.scratch/deep-kernel-phase1/spec.md) records the accepted Phase 1 plan and deferred phase boundaries. Phase 2 holdout selection and complete later-phase protocols are deliberately deferred; proposed specific transfer datasets were not accepted. Recording the agreement does not mean implementation or experiments have been completed.

## References

- [Project proposal](../../FIRSTDRAFT.md)
- [Learning Deep Kernels for Non-Parametric Two-Sample Tests](https://proceedings.mlr.press/v119/liu20m.html)
