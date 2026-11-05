# Branch-specific progress - 2026-11-06

Status: **completed the authorized experiment; stop after local commit**.

- Branch: `experiment/stream-prada-order`, isolated sibling worktree.
- Original main remains `5fb5e07d750a73a0a663a174433bab931ae7568a`.
- Teammate PRADA, pilot split implementation, and Deep Kernel MMD are untouched.
- No push, merge, rebase, cherry-pick, integration PR, or environment modification.

The initial experiment commit `e58d339d44814b85c73927d13c8aa5cd3f561122`
contains the runner and original resource-gated evidence. That run stopped at a
21.12-minute safety-adjusted projection under the required 20-minute gate.
Its files/manifests are preserved; the original Thai report is archived as
`REPORT_PREFLIGHT_TH.md`.

The user explicitly approved a 25-minute gate. `config_25min.json` changes only
`resource_gate_seconds` from 1200 to 1500. The first approved attempt exposed
relative-config provenance path handling and failed before calibration. Its
failure record is retained. The fixed runner completed in a fresh directory:
`results/seed20261106_25min_retry1`.

Completed: 200 benign calibration streams, 200 held-out benign streams, 1,000
permutations per each of three orderings at each of three ratios (9,000 mixed
streams), 9,000 paired comparisons, full trajectories for preselected examples,
maximum scores, alerts, prefix alarms, conditional delays/censoring, runtime,
process/GPU peak memory, conditional uncertainty, graphs, and Thai report.

Findings: ordering changes any-alert decisions in 54.9% of triplets at actual
10.15625% attack and 49.6% at 25%. Held-out benign FPR is 34/200 = 17%.
All 50% schedules alert on benign query 102 before attack query 111: any-alert
100% is not attack-detection 100%, and detection delay is null/ineligible.
No threshold or prefix was changed after seeing results. No novel detector,
causal mechanism, population FPR control, or deployable improvement is claimed.

Verification: focused unit/parity suite passes 8 tests. Added regression tests
first for canonical JSON bytes and relative-path provenance. Three actual-query
parity streams match the upstream precomputed reference exactly. Query pools,
model files, embedding hash and split audit match the initial blocked run.
The independent evidence audit validates all 9,000 schedule hashes, counts,
thresholds, delays, summaries, saved examples, original source/artifact hashes,
and three gzip roundtrips. Outcome/trajectory/difference graphs were inspected.

Fixed an evidence portability bug found during continuation: the first commit
normalized Windows CRLF evidence while its manifests described original CRLF
bytes. Evidence now has Git text conversion disabled, restoring the exact
original hashed bytes without changing measured values or manifests. New runner
JSON writes explicit LF. Verify staged blob bytes, not only working files.
Full CSVs remain ignored locally; commit the lossless gzip copies. No deliverable
file exceeds 1 MB. Postprocessing has separate source/output hashes.

Final checks before local commit: run focused suite and evidence audit, verify
all staged paths are inside `stream_prada_order/`, verify staged source/artifact
bytes and gzip contents against recorded hashes, confirm main SHA and original
checkout cleanliness, and check active branch immediately before committing.
After that commit, stop. This branch must remain independent indefinitely.

Final verification completed: all 8 tests passed; working-file and staged-only
evidence audits passed, including a fresh temporary copy containing gzip tables
and no uncompressed CSVs. All 39 staged paths are experiment-scoped (2.89 MB
total; largest file 757,153 bytes). Historical JSON values/manifests are identical
to the previous commit; restored original CRLF bytes satisfy their hashes.
Thai text encoding and all graphs were verified. Whitespace checks pass with
CRLF recognized for byte-preserved evidence. Main SHA and checkout are unchanged.
