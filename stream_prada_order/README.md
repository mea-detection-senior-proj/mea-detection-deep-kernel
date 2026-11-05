# Stream PRADA order sensitivity

This directory belongs only to `experiment/stream-prada-order`. Never integrate
it into `main` or another integration branch, open a PR, push without explicit
authorization, or transfer its commits. Before every commit verify the branch.
The original checkout and all teammate detector implementations remain untouched.

## Reproduction

Use the existing `senior` Conda environment; no packages were installed or changed.
Run from the isolated worktree root:

```powershell
conda run --no-capture-output -n senior python -m unittest discover -s stream_prada_order/tests -v
conda run --no-capture-output -n senior python stream_prada_order/experiment.py `
  --data-root '../llm-mea/data/model_leeching' `
  --output stream_prada_order/results/new_run
```

The external dataset directory is read only. Alternatively download the official
[processed query artifact](https://huggingface.co/datasets/ShuzeLiu11/mmd-llm-mea-detection-data)
outside Git and point `--data-root` at its `model_leeching` directory. Follow the
original data terms. File hashes in `config.json` must match. The runner requires
the cached BGE snapshot named by the frozen revision, loads it locally only, uses
evaluation mode and inference mode with all parameter gradients disabled, and
applies normalized embeddings with no query prefix and maximum length 512.
`--model-root` may point to a different directory containing that snapshot.
Model file hashes and the resulting embedding hash are recorded. Floating point
reproduction across different hardware/library versions is not guaranteed.

The configuration is frozen before the first run. Existing result directories
are never overwritten. The runner verifies branch, upstream Git blob, dataset
hashes, source grouping, finite normalized embeddings, memory availability,
CUDA execution, and real-query reference parity. The 1,200-second gate covers
setup, encoding and stream evaluation. Five calibration timings and five paired
pilot permutations per ratio project the remaining work with a 2x safety factor;
an excessive projection stops for user approval. A deadline is checked between
streams. An individual native operation cannot be interrupted by this check.

## Protocol and interpretation

- Actual normal and attack queries come from the repository's `model_leeching`
  artifact. No sentences are synthesized and no LLM/API calls are made.
- Reuse `pilot/protocol.py` without edits: transitively join shared IDs, normalized
  text and attack source contexts; remove cross-label collisions and deduplicate.
  Its calibration and test partitions supply the two disjoint pools. Train and
  validation partitions are unused. Up to 1,000 queries per pool are sampled by
  a fixed RNG permutation. Recorded audits and hashes describe the exact pools.
- Stream length 256; fixed benign prefix of 110 queries; first attack at query
  111 for every condition. Attack counts are rounded from 10%, 25%, and 50%:
  26, 64, 128. Effective fractions are reported separately from requested values.
- A fixed query set is selected per ratio. For each of 1,000 paired seeds,
  shuffle within-label orders once and share them across conditions. `random`
  shuffles the tail after its forced first attack; `clustered` places all attacks
  contiguously after the prefix; `interleaved` spreads attacks at evenly spaced
  positions in the suffix. Random is conditional on the common prefix and onset.
- Use minimum L2 distance to the growing set, initial growth distance 0,
  monotonically nondecreasing max(previous, mean minus population SD) threshold,
  all minimum distances in history, inclusive three-sigma filtering with the
  upstream fallback, and Shapiro-Wilk at every query after **more than 100**
  distances (first eligible query 102). No subsampling at this stream length.
- Share one linear P95 threshold from 200 benign calibration streams across all
  ratios and orderings. Score = 1 minus minimum W; alert uses strict W < delta,
  delta = 1 minus P95. Score each entire stream after the first alert.
- Held-out benign FPR uses 200 streams sampled without replacement within each
  stream from the held-out benign pool; queries recur across streams. Mixed
  streams also reuse this evaluation pool. Calibration contains no test sources
  according to the repository grouping audit.
- Delay = first alert query minus 111, with zero denoting an onset-query alert.
  Report prefix false alarms separately. Undetected streams are right censored;
  median delay among detections is conditional and can favor low-detection rules.
- Wilson intervals describe conditional Monte Carlo uncertainty over these
  schedules or benign stream draws. They do **not** establish population FPR or
  generalization across datasets, query sets, sources, encoder models, or lengths.
  Paired score quantiles describe the permutation distribution, not a confidence
  interval for a population mean. These are simulated schedules, not real traces.

## Reference and acceleration

The unchanged local [stream reference](../PRADA/prada_stream_detector.py) matches
[LabRAI's implementation](https://github.com/LabRAI/mmd-llm-mea-detection/blob/af9420da12a03bf321a2218870a68f7b38f5787c/PRADA/prada_stream_detector.py)
at Git blob `5f951afa8cc750c5497e4efd793100db0648ad6a`. The reference is a
PRADA-style embedding adaptation; this experiment does not claim parity with
an independently retrieved original image-classification PRADA implementation.
The new loop reuses the reference's trimming function and uses shared CPU
float32 `torch.cdist` matrices for distance lookup. Unit parity covers both
upstream distance modes, duplicates, scores, W trajectories, growth count and
first alerts. Three real-query streams additionally gate the experiment against
the precomputed reference mode with W absolute tolerance 2e-5 and exact growth
counts/first alerts. Shared matrices can differ slightly from per-stream matrix
products due to floating point arithmetic. The reference's direct-norm and cdist
modes themselves differ on duplicate embeddings; the tests respect each mode's
distance computation rather than hiding that difference by loosening tolerance.

## Artifacts

Results contain frozen provenance, full per-stream scores, paired differences,
calibration scores, held-out benign scores, three example trajectory triplets,
summary statistics, graphs, measured gates, and artifact hashes. Query text,
datasets, encoder weights, embeddings, caches and secrets are never committed.
Example trace indices refer to the ordered hash lists in `metadata.json`.
The calibration pool indexes its own matrix; evaluation indices refer to the
benign list followed by the attack list. Runtime is measured per stream and for
the complete run; peak working set includes Python, model and shared matrices.
GPU memory statistics describe this process's PyTorch allocation, not total
device use. See `REPORT_TH.md` and `PROGRESS.md` for results and verification.

The first run stopped at the initial resource projection gate. Rebuild only its
null assessment and resource graph without executing the experiment:

```powershell
conda run --no-capture-output -n senior python stream_prada_order/summarize_blocked.py stream_prada_order/results/seed20261106
```
