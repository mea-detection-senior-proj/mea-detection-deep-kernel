---
status: accepted
---

# Preserve the upstream fixed-kernel baselines

The fixed RBF and Multi-RBF baselines must be the original methods extracted from LabRAI/mmd-llm-mea-detection, rather than newly designed substitutes. Retain the original RBF formula, benign median-bandwidth selection, Multi-RBF equal weighting at scales 0.5/1/2/4, and unbiased MMD statistic. Attack-informed bandwidth learning is a separate experimental control and must not change or replace these fixed baselines.

## Verified provenance

The upstream source is [MMD_detection/mmd_detector_gpu.py at commit 7532c25b973ef13f3f971e73a40ff46d469e3fea](https://github.com/LabRAI/mmd-llm-mea-detection/blob/7532c25b973ef13f3f971e73a40ff46d469e3fea/MMD_detection/mmd_detector_gpu.py). Its upstream Git blob SHA is `25844d41a113dfc520c4fbcb136afda82babc841`. The retained local file has the same Git blob SHA after Git's path-based normalization, and has no working-tree diff. Provenance was checked on 2026-11-04.

## Existing extraction limits

The current modular detector has matching core formulas for ordinary valid bandwidths, but has not been established here as behaviorally identical for all inputs. The legacy kernel floors bandwidths at 1e-12; the modular detector does not floor tiny positive bandwidths. Bandwidth input validation and the order and dtype of reference-score averaging also differ. Any extraction advertised as faithful must retain or explicitly account for these differences and be checked against the retained upstream implementation before experimental claims are made.

The current modular evaluation additionally changes calibration, percentile interpolation, and sampling behavior. Legacy calibration uses individual benign-pair MMD scores while test scoring averages reference comparisons; the modular evaluation calibrates that averaged statistic directly. These are evaluation-protocol changes and must not be described as an unchanged original detector.

## Common evaluation protocol

Interview Q10 accepted preserving the upstream baseline computation within a common evaluation protocol shared by all five methods. The primary comparison uses shared evaluation windows and common calibration rules, with method-specific thresholds, and explicitly reports the adapted evaluation protocol. Retain the original complete script for provenance, differential verification, and separate reproduction experiments; do not describe the adapted primary comparison as an unchanged reproduction of the original paper. The accepted calibration and sampling defaults are recorded in [ADR 0001](0001-query-efficiency-and-unseen-attack-evaluation.md) and the [Phase 1 specification](../../.scratch/deep-kernel-phase1/spec.md). No detector implementation was changed during this interview.
