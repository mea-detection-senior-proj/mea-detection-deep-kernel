# Clean Architecture migration record

Implemented on 2026-11-04 against the
[accepted structural spec](../.scratch/clean-architecture/spec.md) and
[ADR 0003](adr/0003-restructure-active-code-and-archive-legacy-detectors.md).
This completes the structural milestone for the three existing methods. It does
not complete the five-method Phase 1 benchmark or establish new detector results.

## Inventory and preservation

The starting commit was `59d626d7a325425ab7e81a666ca6c3140eb82bb8`.
`git status --porcelain=v1 --untracked-files=all` was empty before implementation.
Ignored local resources were inventoried separately rather than treating a clean
tracked tree as proof that no local work existed.

All 1,267 files selected for legacy relocation were SHA-256 hashed before the move
and verified afterward. Their original and new paths, sizes and hashes are in
[the archive manifest](../old-detectors/manifest.json), with roles and provenance
in [the archive index](../old-detectors/INDEX.md). No historical source or output
was deleted or rewritten. Active references were checked before relocation; the
only active-test dependency was the original MMD numerical reference, now loaded
explicitly by file location without writing archived bytecode.

All 297 inventoried research-input and active-artifact files outside transient
test storage were also hash-verified unchanged after relocation. They include
the raw data, local encoder, embedding caches, old protocol locks and results.
The local preservation inventory is `artifacts/migration-protected-resources.json`.
Ignored resources remain local and are not automatically tracked by Git.

## Responsibility mapping

| Previous source | Active responsibility |
| --- | --- |
| `data_pipeline/datasets.py` | `mea_detection/data/datasets.py` for in-memory rules and `data/io.py` for readers/discovery |
| `data_pipeline/windows.py`, `capacity.py` | `mea_detection/data/windows.py`, `capacity.py` |
| `experiments/audit_data.py` | `mea_detection/data/audit.py` for numerical checks; `data/readiness.py` for audit I/O |
| `data_pipeline/embeddings.py` | `mea_detection/embeddings/encoder.py`, preserving cache keys and generation behavior |
| `detectors/mmd/detector.py` | `mea_detection/detection/mmd.py` and shared `detection/kernels/fixed.py` |
| `detectors/deep_kernel_mmd/model.py` | `mea_detection/detection/kernels/deep.py` |
| `detectors/deep_kernel_mmd/training.py` | numerical `detection/training.py`, validation in `detection/settings.py`, persistence in `detection/checkpoints.py` |
| `evaluation/windows.py` | `mea_detection/evaluation/windows.py` |
| `experiments/locked.py` | `mea_detection/experiments/locked.py`, numerical policy in `protocol.py`, persistence/integrity in `protocol_io.py` |
| `experiments/workflow.py` | `mea_detection/experiments/workflow.py`, the single end-to-end lifecycle |
| `experiments/summarize_comparison.py` | `mea_detection/evaluation/comparison.py` for rates/endpoints, `reporting/comparison.py` for saved-evidence validation and `reporting/render.py` for presentation |
| Former command handlers | `mea_detection/cli/`, invoked by `mea_detection/__main__.py` |

`paths.py` anchors project resources to the root package independently of caller
depth. `identity.py` hashes all active-package Python sources and excludes the
archive. `runtime.py` contains deterministic Torch setup. Configuration resolution
remains reusable outside the CLI; it does not import CLI handlers.

Numerical rules use Torch and NumPy directly, without filesystem access, encoder
loading, device selection, checkpoint serialization or report rendering. Detection
receives prepared embeddings. The workflow accepts an `encode` callable for the
real external variation needed in fixture tests; protocol preparation can also
receive a dataset loader. There is no new framework or parallel orchestration.

`tests/test_architecture.py` enforces forbidden import boundaries and checks the
active-module import graph for cycles. It also checks archived Python sources
against the recorded hashes. Normal unittest discovery uses `-s tests`;
`pytest.ini` limits pytest discovery to the same active test area.

## Compatibility and intended command changes

Use [the current command guide](RUN_EXPERIMENTS.md). The unlocked fixed-only runner
was removed; the main command now always uses the shared-protocol lifecycle.
Old imports and command modules are intentionally unsupported. Replacement JSON
examples retain scientific settings, select the same local BGE encoder and use
new migrated destinations. Examples that formerly omitted encoder settings now
name the local model explicitly; previously they failed pinned-remote validation
without a command-line override. Existing saved configs under artifacts are intact.

Relocation changes source identity. Execution rejects incompatible protocol source
identity, and new checkpoints record format/source/lock identity. Reload verifies
format and source, and can verify an expected protocol ID. Historical identities
are not rewritten to pass. Reports consume immutable saved evidence: a historical
run and lock may be reported together if they agree, but incompatible source
identities cannot be mixed in one comparison. The retained pre-migration outputs
remain historical evidence, not newly certified migrated runs.

## Validation evidence

- Before migration: all **32 existing unittest checks passed**, with no observed
  pre-existing test failures. The baseline suite completed in 17.798 seconds.
- Before moving active source, captured deterministic three-method scientific
  records in `tests/fixtures/migration_expected.json`. The fixture uses seed 42,
  float64 computation, float32 deterministic embeddings and actual data grouping,
  partitioning, sampling, fitting, selection, calibration and persistence.
- After migration: **37 unittest checks passed**, including the original coverage,
  dependency/archive checks, public operation coverage, migration fixture/replay
  acceptance and incompatible-source reporting. Local output is retained in
  `artifacts/migration-tests.log`.
- Fixture comparisons cover per-window scores, calibration scores, thresholds,
  summaries, report rates/endpoints, partition manifests, pools and training
  records. Numeric tolerance is `rtol=1e-10`, `atol=1e-12`; identities, grouping and
  other nonnumeric records match exactly. Timing and source-path identities are
  intentionally outside numerical equivalence.
- Fixed-kernel tests compare scalar-reference and preserved-original MMD values,
  benign median bandwidth and reference-averaged scores. Existing deep-kernel
  equation, gradient and objective checks pass. Moving source does not resolve
  the known edge differences recorded in ADR 0002.
- Selected checkpoints reload frozen at the saved dtype with matching fixture
  scores. Altering only held-out embeddings leaves selected model parameters and
  calibrated thresholds unchanged. Wrong protocol and incompatible source IDs
  fail explicitly.
- Public `run`, dry-run, `audit`, `prepare` and `report` operations are tested with
  synthetic data. Dry-run performs no writes, encoding or GPU allocation. Protocol
  reuse does not re-encode. Reports regenerated from saved results match originals
  without retraining. Existing no-overwrite, tampering, incomplete/failed-run,
  duplicate-result and coverage checks pass.
- Real-data command preflight passed for `deep_pure.json`, window 100, seed 42 on
  CPU, without creating `artifacts/migrated_cpu_v1`. Root command and audit/report
  help were also executed. Every active JSON example resolves its encoder and
  configuration successfully. Larger grids remain subject to capacity checks.
- `git diff --check` passed. The full archive and protected-resource inventories
  were hash-verified after relocation.

## Limits and deferred work

No full real-data training grid, GPU execution or new superiority experiment was
run. Validation uses deterministic synthetic embeddings in place of the external
encoder, plus real-data preflight. The fixed-kernel tiny-bandwidth floor, input
validation and reference-averaging differences documented in ADR 0002 remain
identified scientific follow-up work; they were not silently changed by migration.

Learned-bandwidth RBF, the MLP classifier and remaining five-method acceptance
belong to the subsequent Phase 1 milestone. Phase 2 transfer, Phase 3 mixed
training and the dashboard remain deferred. Existing exploratory configuration
values, including window 250 and its integer attacker-count behavior, were retained.
