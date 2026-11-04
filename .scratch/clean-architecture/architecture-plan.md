# Active-code architecture migration

Status: accepted design; implementation not started by this interview.

Implementation handoff: [Clean Architecture spec](../clean-architecture/spec.md), published separately with status `ready-for-agent`. This plan retains the accepted design rationale and source/archive mappings.

The user confirmed shared understanding in Q13 on 2026-11-04. This plan completes the architecture interview, not the migration or Phase 1 benchmark. The interview is conducted in Thai; durable documentation is written in English. See [ADR 0003](../../docs/adr/0003-restructure-active-code-and-archive-legacy-detectors.md) and the [decision history](architecture-interview.md).

## Goal and milestone boundary

Organize active research code by responsibility and execution flow, with explicit dependency rules. Favor small functions and existing behavior over frameworks, wrappers, or speculative extension points. Use one root-level Python package, `mea_detection/`, without a `src/` wrapper. `mea-detection` may be the project name; this plan does not rename the repository directory.

The first milestone migrates the existing fixed RBF, fixed Multi-RBF, and pure-trained deep-kernel workflow, preserves uncommitted implementation work, archives unused legacy code and associated outputs, and updates usage documentation. Adding learned-bandwidth RBF and the MLP classifier is a separate subsequent milestone. The full five-method real-data comparison remains required for Phase 1, but is not required to establish that the structural migration works.

## Target layout

```text
mea_detection/
  data/          input loading, duplicate audit, partitions and window sampling
  embeddings/    frozen encoder integration and embedding cache
  detection/     detector fitting and scoring
    kernels/     RBF, Multi-RBF and deep-kernel calculations
  evaluation/    calibration, rates and minimum effective window size
  experiments/   experiment lifecycle, protocol rules and run coordination
  reporting/     tables, plots and reports from saved evidence
  cli/           command parsing, runtime setup and dependency composition

configs/
data/            raw and prepared research inputs, not Python source
artifacts/       active models, caches, protocols and run artifacts
old-detectors/   archived source and associated historical outputs
tests/
docs/
```

Use folders only where actual migrated code warrants them. Do not create empty method implementations, mixed-training modes, dashboards, plugins, or generic framework scaffolding. Kernel code belongs inside detection: a classifier is a detector but does not need a kernel.

## Dependency and responsibility rules

- Scientific calculations may depend directly on Torch and NumPy. Do not invent tensor wrappers. Keep mathematical computations independent of file access, model downloads, command parsing, and runtime device selection; operating on tensors already placed on a device is permitted.
- `data` owns query/group identities, duplicate rules, splitting and sampling. Separate loaders/writers from in-memory transformations within this responsibility. It does not depend on detectors or experiment runners.
- `embeddings` implements the frozen encoder and cache integration. It does not select detector methods or experimental outcomes. Preserve encoder content identity, generation dtype and normalization records.
- `detection` receives prepared embeddings and permitted training/validation inputs, and returns fitted state or scores. It does not choose datasets, perform experiment-level partitioning, calibrate alert thresholds, or write reports. Separate checkpoint serialization from numerical fitting/scoring. Scientific detection modules do not import CLI, experiment orchestration, reporting, encoder loaders or persistence implementations.
- `evaluation` owns score-based calibration, strict alert decisions, rates and endpoint calculations. Accept scores or a scoring interface without depending on a particular concrete detector. Its numerical rules do not load datasets or train models.
- `experiments` owns the lifecycle: preflight, shared protocol preparation, fitting/selection, freezing, calibration, evaluation and artifact-completion rules. Pass external loaders, encoder access and persistence through small interfaces or callables where needed. Keep protocol validation independent from concrete file handling; keep one lifecycle rather than introducing a competing runner.
- `reporting` consumes saved result records and metadata to produce tables, plots and the English report. It must not refit models or select thresholds. Preserve completeness, compatibility and coverage validation before producing a completed comparison.
- `cli` composes concrete integrations and invokes the workflow. Keep device setup and configuration-file parsing here or in focused runtime helpers. Other modules do not import the CLI.
- Keep I/O implementations beside their owning responsibility in clearly separated modules; do not recreate four architectural layers inside every folder. Introduce shared interfaces only for actual substitution needs, including detector scoring and fixture encoder replacement. No dependency-injection framework, universal detector plugin system, or compatibility wrappers for every old command.

## Migration map

| Current source | Target responsibility |
| --- | --- |
| `data_pipeline/datasets.py`, `windows.py`, `capacity.py`, provenance records | `mea_detection/data/`; separate input I/O from rules |
| `data_pipeline/embeddings.py` | `mea_detection/embeddings/` |
| `detectors/mmd/`, `detectors/deep_kernel_mmd/` | `mea_detection/detection/`, with shared kernel calculations in `kernels/` |
| `evaluation/windows.py` | split numerical evaluation from lifecycle/I/O across `evaluation/` and `experiments/` |
| `experiments/workflow.py`, `locked.py`, protocol/run artifact helpers | `mea_detection/experiments/`; extract concrete I/O and runtime setup from coordination |
| `experiments/summarize_comparison.py` | reporting calculations/rendering in `reporting/`, command parsing in `cli/` |
| existing run, prepare and audit command entry points | `mea_detection/cli/`, retaining reusable functions for tests |

These are responsibility mappings, not instructions to move mixed-responsibility files unchanged. Update callers, tests, fixtures, configuration paths and documented commands together. Resolve project-relative paths independently of the old source-file depth. Update code-identity enumeration to cover the new active package and exclude archived implementations from active runtime identity.

## Archive and protected resources

Read-only inspection identified the following unused legacy groups: `MMD_detection/`, `pilot/`, `PRADA/`, `SEAT/`, `CAP/`, `DATE/`, `Mahalanobis/`, `PseudoEnergy/`, `new_main_experiment/`, `review_experiment/`, `supplementary_experiments/`, and `run_all_paper_experiments.sh`. Archive these under `old-detectors/`, preserving their internal layout and associated historical outputs, including `experiment_result/` where no active dependency remains.

`query_extracter/` contains standalone stored-data conversion scripts, not a dependency of the active benchmark. Apply the accepted unused-code criterion to archive it as legacy tooling; document its original role rather than presenting it as a detector. Recheck references at implementation time before moving any path. A new active dependency requires retaining or extracting the required behavior, not blindly moving it into the archive.

Protect root `data/`, active encoder resources such as `artifacts/models/bge-small-en-v1.5`, active embedding caches, and artifacts still referenced by active configurations, including `artifacts/model_leeching_protocol_v1`. Do not move all of `artifacts/` indiscriminately. Preserve existing resource locations for this migration where practical; distinguish an incompatible historical lock from an unused file. Do not delete caches or rewrite scientific records merely to simplify the tree.

At migration time, write an archive index with original and new paths, purpose, provenance, and execution limitations. Preserve the retained upstream detector source required by ADR 0002. `old-detectors` is not a normal Python import name: the numerical differential test must load the original source explicitly by file path, with no active-runtime dependency on the archive. Restrict normal test discovery to active `tests/` so archived test suites are not collected. Do not require historical environments or commands to remain runnable.

## Commands and compatibility

Use one primary end-to-end invocation from the repository root. A suitable command surface is `python -m mea_detection run`, with focused `audit`, `prepare`, and `report` operations and a no-training dry-run option. These are target commands, not commands implemented by this document. Do not expose every fitting or scoring function as a command. Report regeneration must work from saved evidence without retraining.

Old commands and config shapes may change. Provide working replacement examples and a concise migration guide. Preserve accepted settings, method identities and scientific semantics; do not add wrappers solely to keep old imports alive. With no `src/` wrapper, root execution is sufficient initially; add packaging metadata only if actual installation requirements justify it.

Keep historical evidence inspectable and immutable. Preserve existing artifact conventions unless a necessary structural change requires explicit compatibility metadata. Moving source changes code identity; do not pretend old locks match by rewriting their recorded paths/hashes. Validate configuration, code, data, encoder, split, draw and method identities as applicable and reject incompatible reuse/comparison clearly. New runs must use new output destinations, retain running/complete/failed states, and save replayable checkpoints. This milestone does not promise that every old checkpoint or lock can resume.

## Implementation sequence

1. Inventory the current working tree, including uncommitted and untracked implementation work, active inputs, archive candidates and their references. Establish existing test results and deterministic scientific fixture outputs before structural edits; record pre-existing failures separately.
2. Establish the root package and command composition. Move one responsibility at a time, updating imports, root/path resolution and code-identity enumeration. Retain one operational workflow while moving; the target need not be delivered as a single unreviewable change.
3. Separate scientific rules from I/O/runtime setup, especially the currently mixed locked workflow, dataset loading/splitting, and deep-kernel training/checkpoint handling. Preserve mathematical behavior, validation and error handling. Keep known scientific corrections separately identifiable from structural edits.
4. Relocate verified unused code and associated outputs, record the archive map, and update original-source differential loading. Preserve inputs and resources required by the active workflow.
5. Run the migration acceptance checks, update English run/config examples and mark obsolete documentation clearly. Record what passed and any known limitations.
6. Finish the structural milestone. Implement the two missing controls and remaining Phase 1 behavior afterward under the scientific spec; do not mark the full benchmark complete on the basis of migration tests.

## Acceptance evidence

- The three existing methods run through the new end-to-end workflow with synthetic data and fixture embeddings, using actual splitting, sampling, fitting, calibration and reporting.
- Deterministic scientific fixture outputs remain equivalent within declared tolerances; exclude timing and timestamps. Preserve upstream-baseline differential checks, edge behavior coverage already present, and numerical deep-kernel checks. Record existing discrepancies rather than treating them as newly proven fidelity.
- Selected model state saves and reloads with equivalent scores; checkpoint selection and calibrated thresholds do not depend on held-out test observations.
- Shared draws, protocol integrity, failure states, no-overwrite behavior and incompatible-run rejection continue to work. Do not weaken existing coverage, duplicate-result or completion checks while moving code.
- Audit and dry-run operations load no encoder or GPU and create no run artifacts. Existing command capabilities remain available under documented replacements.
- Report generation from persisted fixture evidence includes all three current methods without retraining. Later five-method acceptance remains part of the Phase 1 spec.
- Check active-package imports for cycles and forbidden dependencies, and confirm archived tests are excluded from normal discovery. A focused import-rule check is sufficient; no architecture framework is required.
- Active configs resolve required data/model/cache resources. The archive index matches actual moved files; original provenance and historical evidence remain available.
- Required existing checks pass or pre-existing failures are explicitly accounted for; a migration regression is not excused as a pre-existing problem. No full real-data training grid is required for structural acceptance.

## Deferred work

The learned-bandwidth RBF, MLP classifier, remaining five-method Phase 1 acceptance, and full real-data tables/plots/report follow this migration milestone. Phase 2 transfer, Phase 3 mixed training, and the offline dashboard retain their accepted later placement. Do not implement unused future detector modes or claim new scientific results during migration.
