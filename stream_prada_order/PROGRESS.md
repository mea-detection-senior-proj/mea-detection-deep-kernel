# Branch-specific progress — 2026-11-06

Status: **resource-gated; ordering outcomes remain unmeasured**.

- Inspected clean checkout at main `5fb5e07d750a73a0a663a174433bab931ae7568a`;
  no local/remote experiment branch existed. Created a separate sibling worktree
  on `experiment/stream-prada-order` from that exact local main commit.
- Read repository README, dependencies, PRADA stream/base, and pilot split code.
  No pre-existing AGENTS.md applied. Did not change any existing tracked file.
- Matched upstream stream reference Git blob and recorded pinned model/data hashes.
- Wrote tests first: initial suite failed because `experiment` did not exist.
  Added runner/config. Found direct-vs-cdist duplicate numerical differences in
  parity testing and corrected the test to respect the two upstream modes.
- Ran `conda run --no-capture-output -n senior python -m unittest discover -s
  stream_prada_order/tests -v`: **6 tests passed**. The earlier implementation
  parity run had 1 failure; final suite has none. Conda on this host can return
  shell exit 0 despite reporting a child failure, so actual unittest output is
  the evidence rather than the wrapper exit status alone.
- Ran the README experiment command with output `results/seed20261106`.
  Encoded 3,000 actual queries and passed three real-query parity gates exactly.
  Ran five calibration benchmark streams, then stopped on the first projected
  budget failure: 1,267.1267 seconds including 2x safety vs 1,200 allowed.
- Preserved gate, parity, provenance, explicit null assessment, artifact hashes,
  and a visually inspected resource graph. No detector threshold, outcome rates,
  ordering differences, or detection delays were measured.
- Requested explicit permission for a new run with a 25-minute gate. No extension
  or rerun is authorized by silence. Do not discard or overwrite this blocked run.
- Added Thai report, reproducibility documentation and durable isolation rules.

Remaining: approved new-run budget; full calibration; paired order pilot; 1,000
permutations per ordering/ratio; held-out benign FPR; delay/trajectory summaries;
outcome graphs and updated Thai report. No scientific conclusion about order
sensitivity is supported yet.

Before local commit: verify active branch, rerun focused suite, check all new
files/staged paths and sizes, ensure all source/artifact hashes match, and verify
original checkout clean with unchanged main SHA. Stop after the local commit.
Never push or integrate this branch without a new explicit instruction.

Final verification completed: focused suite passed again (6 tests, 0.704 s),
all saved artifact/source hashes matched, all deliverable files were under 1 MB,
the original checkout was clean, main still pointed to the exact base SHA, and
all staged paths were restricted to `stream_prada_order/`. A directory-scoped
`.gitattributes` preserves experiment text bytes across Windows checkouts.
