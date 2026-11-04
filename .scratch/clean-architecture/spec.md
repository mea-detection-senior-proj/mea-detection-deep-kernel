# Clean Architecture Migration for Model Extraction Traffic Detection

Status: ready-for-agent

Design confirmed on 2026-11-04 in interview Q13. This specification covers the structural migration milestone, not completion of the five-method Phase 1 benchmark. It describes work to be done; publishing it does not perform the migration or establish new experimental results.

## Problem Statement

The researcher needs a repository that is easy to navigate, extend and verify while comparing methods for detecting model extraction traffic. Active data preparation, embedding, detector, experiment and reporting code currently coexists with original detector implementations, exploratory Pilot work, older experiment scripts and historical outputs. Several active modules mix scientific rules with runtime setup and file persistence, making changes harder to reason about.

The researcher wants to preserve the scientific protocol, existing implementation work and historical evidence while organizing the active workflow around its research responsibilities. Unused code and its associated outputs should remain available as reference material rather than being deleted or maintained as competing active workflows. Simplicity matters more than preserving every old command or config format.

## Solution

Migrate active code into one root-level Python package named `mea_detection`, without a source-directory wrapper. Organize it around data, embeddings, detection, evaluation, experiments, reporting and command entry points. Enforce separation through dependency rules and small interfaces rather than generic architectural layers or frameworks.

Complete the migration using the existing fixed RBF, fixed Multi-RBF and pure-trained deep-kernel methods. Preserve current uncommitted work, numerical behavior, scientific constraints, replayable new checkpoints and protocol integrity. Archive verified unused implementations and associated historical outputs in the repository-root `old-detectors` directory, documenting provenance and relocation.

Provide one main end-to-end command and focused audit, preflight, protocol preparation and report operations. Verify the migrated workflow with synthetic data and fixture embeddings, retain original-baseline numerical checks, and document the replacement usage in English. Add learned-bandwidth RBF and the MLP classifier in a separate subsequent milestone.

## User Stories

1. As a researcher, I want one active implementation package, so that I know which code drives current experiments.
2. As a researcher, I want folders organized by research responsibility and execution flow, so that I can locate a change without learning generic architecture layers.
3. As a researcher, I want the package directly under the repository root, so that the layout stays simple.
4. As a maintainer, I want a valid Python package name, so that ordinary imports work reliably.
5. As a researcher, I want a dedicated detection module, so that later methods can join the comparison without creating another pipeline.
6. As a maintainer, I want kernel implementations grouped within detection, so that classifiers are not forced through a kernel abstraction.
7. As a researcher, I want query loading, duplicate auditing and purpose-separated partitions grouped coherently, so that data preparation remains understandable.
8. As a researcher, I want frozen encoder integration and embedding caching separated from detection, so that encoder behavior does not become detector-specific.
9. As a researcher, I want detectors to receive prepared embeddings, so that scoring does not silently reload or repartition data.
10. As a researcher, I want scientific calculations separated from file access and runtime setup, so that I can verify them with small deterministic inputs.
11. As a maintainer, I want direct Torch and NumPy use where calculations need them, so that restructuring does not require tensor wrappers.
12. As a maintainer, I want functions and small interfaces where sufficient, so that the architecture does not add unnecessary classes or frameworks.
13. As a researcher, I want experiment coordination to own the lifecycle, so that preparation, fitting, freezing, calibration and testing remain consistent.
14. As a researcher, I want evaluation rules separated from concrete detectors, so that calibration and rate calculations apply consistently across methods.
15. As a researcher, I want report generation to consume saved evidence, so that regenerating a report does not retrain models or choose new thresholds.
16. As a researcher, I want the current three methods migrated first, so that structural regressions can be distinguished from later scientific additions.
17. As a researcher, I want the two missing learned controls deferred to their own milestone, so that the migration has a clear completion point.
18. As a researcher, I want accepted scientific settings and phase boundaries preserved, so that cleanup does not redesign the study.
19. As a contributor, I want existing uncommitted and untracked implementation work preserved, so that restructuring does not discard current progress.
20. As a researcher, I want unused detector implementations archived, so that they remain available without cluttering active execution.
21. As a researcher, I want unused legacy experiment runners and conversion tooling archived too, so that obsolete entry points are clearly identified.
22. As a researcher, I want historical outputs stored with their legacy context, so that earlier evidence remains interpretable.
23. As a reviewer, I want original and archived locations recorded, so that I can trace provenance after relocation.
24. As a researcher, I want the complete original MMD implementation retained, so that numerical verification and provenance remain possible.
25. As a reviewer, I want active fixed-kernel methods checked against the preserved original source, so that archiving does not weaken baseline verification.
26. As a maintainer, I want archived code excluded from active execution and normal test discovery, so that old environments do not become active dependencies.
27. As a researcher, I want required raw data preserved, so that cleanup cannot remove experiment inputs.
28. As a researcher, I want active encoder resources and embedding caches protected, so that archiving does not break or unnecessarily invalidate current preparation.
29. As a researcher, I want artifacts referenced by active configs identified before relocation, so that an old-looking directory is not incorrectly treated as unused.
30. As a maintainer, I want project-relative paths resolved independently of source-file depth, so that moving modules does not change input locations accidentally.
31. As a researcher, I want one primary end-to-end command, so that running the workflow remains straightforward.
32. As a researcher, I want a data audit operation, so that I can inspect readiness without loading an encoder.
33. As a researcher, I want a dry-run preflight, so that unsupported work is identified before expensive execution.
34. As a researcher, I want shared protocol preparation retained, so that methods can use compatible partitions and draws.
35. As a researcher, I want reports regenerated from saved results, so that presentation changes do not require training again.
36. As a researcher, I want working replacement commands and configs documented, so that changed entry points are easy to adopt.
37. As a maintainer, I want obsolete commands allowed to change, so that compatibility wrappers do not become another framework.
38. As a reviewer, I want historical artifacts preserved without rewriting their identity records, so that provenance remains truthful.
39. As a researcher, I want incompatible locks and checkpoints rejected explicitly, so that relocated code is not silently treated as the old implementation.
40. As a researcher, I want new checkpoints to reload with equivalent scores, so that fitted detectors remain inspectable and reproducible.
41. As a researcher, I want new runs to use new destinations, so that earlier evidence cannot be overwritten accidentally.
42. As a reviewer, I want running, complete and failed states retained, so that a failed migration run cannot masquerade as completed evidence.
43. As a researcher, I want shared-draw and artifact-integrity checks preserved, so that the cleanup cannot weaken comparison validity.
44. As a researcher, I want calibration target FPR kept distinct from measured FPR, so that restructuring does not change reporting meaning.
45. As a researcher, I want fitting and calibration independent of held-out test observations, so that leakage is not introduced by refactoring.
46. As a maintainer, I want synthetic end-to-end checks at the existing workflow interface, so that the migrated system is tested as a whole.
47. As a reviewer, I want deterministic scientific outputs compared within declared tolerances, so that numerical changes are detected without requiring identical timestamps.
48. As a maintainer, I want lightweight dependency checks, so that the intended separation survives future edits.
49. As a researcher, I want pre-existing failures distinguished from migration regressions, so that structural work is assessed honestly.
50. As a researcher, I want migration acceptance without a complete real-data training grid, so that architectural correctness can be checked at appropriate cost.
51. As a researcher, I want the migration milestone distinguished from the full Phase 1 benchmark, so that completion claims are accurate.
52. As a contributor, I want current English documentation and obsolete-plan notices, so that I do not follow superseded instructions.

## Implementation Decisions

- **Package organization:** use the root-level `mea_detection` package, with data, embeddings, detection, evaluation, experiments, reporting and CLI modules. Keep kernels within detection. Retain separate repository-level configuration, research-input, artifact, archive, test and documentation areas. No repository-directory rename is required. Create submodules only when actual code needs them.
- **Architectural approach:** organize by responsibility and flow rather than folders named after architectural layers. Prefer existing functions and small interfaces. Do not introduce tensor wrappers, a dependency-injection framework, a universal plugin system, or duplicated orchestration.
- **Scientific dependencies:** Torch and NumPy are permitted in numerical code. Separate file access, downloads, command parsing and runtime device selection from scientific calculations. Calculations may operate on tensors already placed on a device.
- **Data ownership:** the data module owns loading, query/group identity, duplicate policy, partitioning, capacity rules and window sampling. Separate concrete loading/writing from in-memory rules; do not depend on detectors or experiment runners.
- **Embedding ownership:** the embeddings module provides frozen encoder integration and cache handling. Preserve normalization, encoder content identity and generation dtype. It must not select detector methods or outcomes.
- **Detection ownership:** fitting and scoring receive prepared embeddings and permitted training/validation inputs. They do not choose datasets, perform experiment-level partitioning, set alert thresholds or write reports. Keep checkpoint serialization separate from numerical fitting/scoring. Numerical detection modules do not import command handling, experiment coordination, reporting, encoder loading or concrete persistence.
- **Kernel ownership:** centralize actual shared kernel calculations inside detection. Preserve the identities of the fixed RBF, fixed Multi-RBF and deep-kernel methods. Do not require every future detector to use a kernel.
- **Evaluation ownership:** calibration, strict threshold decisions, TPR/FPR and minimum effective window size remain numerical rules. Accept scores or a scoring interface without coupling to a particular concrete detector. Do not load datasets or train models inside these calculations.
- **Experiment ownership:** keep one lifecycle for validation/preflight, shared protocol preparation, fitting/checkpoint selection, freezing, calibration, evaluation and completion validation. Receive loaders, encoder access and persistence through focused interfaces or callables where substitution is necessary. Separate protocol policy from concrete file handling.
- **Reporting ownership:** consume saved records and metadata to produce tables, plots and the English report. Preserve compatibility, completeness, duplicate-result and coverage validation before declaring a completed comparison. Reporting must not refit models or choose thresholds.
- **Composition:** command entry points parse configuration, set up runtime dependencies and invoke reusable workflow functions. Other modules do not import the command layer. Keep concrete I/O beside its owning responsibility in separated modules rather than recreating generic layers inside every folder.
- **Interfaces:** preserve the current workflow and scoring test surfaces while allowing import names, function organization and fixture injection to change. Introduce interfaces only for real variation, including interchangeable detector scoring and replacement of the external encoder in tests. Do not widen contracts merely to anticipate deferred methods.
- **Commands:** provide one primary end-to-end operation plus focused data audit, no-training preflight, shared protocol preparation and report regeneration. Reuse the workflow behind these operations; do not expose every internal function as a command. Exact command flags remain implementation choices documented with working examples.
- **Configuration compatibility:** old commands, imports and config shapes may change. Preserve scientific meanings and accepted values, provide replacement examples and migration guidance, and avoid compatibility wrappers solely for obsolete entry points. Root execution is sufficient initially; installation metadata is not required unless a concrete need emerges.
- **Archive inventory:** archive verified unused original detector code, Pilot work, the six other legacy detector families, old experiment runners, legacy batch launch tooling and standalone unused data-conversion tooling. Include associated historical outputs. Preserve internal layout where practical and document the role of non-detector legacy tools. Recheck current references before moving any candidate.
- **Protected resources:** retain active research inputs, frozen encoder resources, embedding caches and artifacts still referenced by current configurations. Do not archive the entire artifact area indiscriminately. An incompatible historical protocol is not automatically an unused resource. Preserve active resource locations where practical; do not clear caches as a cleanup shortcut.
- **Archive contract:** use the repository-root `old-detectors` archive with an index recording original and new locations, purpose, provenance and execution limitations. Historical environments and commands need not remain runnable. Active runtime must not import archived code. Preserve the complete upstream MMD source and load it explicitly by file location only for numerical reference checks.
- **Historical evidence:** preserve records without overwriting or rewriting recorded identities to make old artifacts compatible. Package relocation changes source identity. Keep existing artifact conventions unless a necessary change requires explicit compatibility metadata; no universal old-lock or old-checkpoint resume guarantee is made.
- **Active artifact contract:** update code-identity collection to include the migrated active source and exclude archived runtime implementations. Preserve applicable data, encoder, configuration, split, pool, draw, method and code checks. Reject incompatible reuse/comparison explicitly. Retain new-destination execution, failure records and running/complete/failed states. New-system checkpoints must save and reload with equivalent scores.
- **Migration sequencing:** first inventory current work and capture existing checks and deterministic fixture outputs; then establish the package and composition, move responsibilities incrementally, update callers/path resolution/configs/tests, separate mixed responsibilities, archive verified unused assets, and complete documentation and acceptance checks. Keep known scientific corrections separately identifiable from structural edits. Do not discard uncommitted or untracked implementation work.
- **Scientific invariants:** preserve accepted purpose separation, shared draws, stage-specific randomness, frozen encoder use, checkpoint selection, calibration rules and dataset-separated result meaning. A fitted detector must not be selected using the true attacker fraction or held-out test outcomes. Keep pure-attack training distinct from mixed-traffic evaluation, and retain calibration target FPR versus measured FPR terminology.
- **Milestone boundary:** migrate the three existing methods first. Preserve and relocate any relevant work already present, but do not add the two missing learned controls or expand incomplete scientific features merely to complete the structural migration. Remaining five-method requirements belong to the subsequent Phase 1 implementation milestone.

## Testing Decisions

- **Already confirmed scope:** Q12 accepted migration checks for original-baseline numerics, synthetic end-to-end execution, checkpoint save/reload, protocol integrity and reporting; Q13 confirmed shared understanding. No further interview is required to select this test surface.
- **Primary seam:** use the existing configured experiment workflow, migrated to its new package, as the highest integration interface. Supply small synthetic datasets and deterministic fixture embeddings, replacing only the external encoder. Retain actual grouping, splitting, sampling, fitting, checkpoint selection, calibration, scoring, persistence and reporting. Temporary output storage is sufficient; do not mock every internal stage or create a competing test runner.
- **Good tests:** assert observable scientific records, scores, replay behavior, output completeness, reproducibility, documented errors and resource protection. Avoid private call ordering, exact module layouts beyond intentional import rules, implementation-mirroring expected results, or assertions that require real-data superiority.
- **Behavior preservation:** compare deterministic scientific fixture outputs before and after migration within declared numerical tolerances. Exclude timestamps and timing. Capture current working-tree behavior, including uncommitted work; explicitly record pre-existing failures and discrepancies rather than accepting migration regressions as historical problems.
- **Current-method workflow:** a migrated fixture run includes fixed RBF, fixed Multi-RBF and pure-trained deep-kernel results through their applicable lifecycle. Dataset identities and accepted score/calibration semantics remain intact. Full five-method acceptance is deferred, not waived.
- **Necessary numerical seam:** retain independent scalar-reference and preserved-original comparisons for fixed kernels, MMD and reference-averaged scoring, together with existing edge-case, deep-kernel, gradient and objective checks. Load original source by explicit file location after archiving it. Moving it must not become a claim that previously unverified edge differences were resolved.
- **Checkpoint behavior:** saved selected state reloads with equivalent scores. Frozen parameters, validation-only selection and threshold independence from held-out test changes remain covered. Preserve existing public numerical tests rather than creating another training test framework.
- **Protocol and persistence behavior:** retain shared-draw reuse/tampering, incompatible-lock/config/source detection, no-overwrite, incomplete-run, duplicate-result, coverage and failure-state checks. Old incompatible identities fail clearly; new-system artifacts remain replayable under their documented checks.
- **Command behavior:** new entry points retain audit, full workflow, preflight, protocol preparation and report regeneration capabilities. Dry-run and audit operations do not load an encoder, allocate GPU resources or create run artifacts. Validate public command behavior with fixture inputs rather than private parser details.
- **Report behavior:** reconstruct rates from persisted fixture records and generate reports for all three existing methods without retraining. Preserve measured FPR terminology and completion/integrity checks. Do not weaken existing report semantics during migration.
- **Dependency and archive checks:** use focused import checks to detect forbidden dependencies and cycles. Active runtime is independent of archived implementations; normal test discovery excludes archived test suites, with only the explicit numerical reference test loading original source. No architecture framework is needed.
- **Resource and documentation checks:** active configs resolve protected inputs, encoder/cache resources and retained artifacts; recorded relocations match actual files; required provenance remains available. Verify replacement command/config examples and links. Keep schema and identity validation appropriate to the actual artifact conventions.
- **Prior art:** extend the existing standard-library unittest workflow/CLI tests with fixture embeddings, locked-run integrity/replay tests, scalar/original MMD differential tests, deep-kernel mathematical tests, data readiness/grouping tests and persisted comparison-report tests. Change imports and injection points as needed while preserving their behavioral coverage.
- **Completion evidence:** required existing checks pass or pre-existing failures are separately documented and accounted for; migrated acceptance behavior passes without regressions. A full real-data training grid is not required for this structural milestone. Record executed checks and limitations; authoring this spec does not execute them.

## Out of Scope

- Implementing learned-bandwidth RBF or the MLP classifier, or declaring the five-method Phase 1 benchmark complete.
- Expanding unfinished scientific requirements beyond the structural migration; these remain in the Phase 1 spec.
- Running the complete real-data dataset/seed/grid matrix as a prerequisite for migration acceptance or making new superiority claims.
- Changing the accepted scientific protocol, fixed-baseline identity, encoder, experimental settings or phase sequence as part of cleanup.
- Phase 2 transfer, Phase 3 mixed-training implementation, unused future-mode scaffolding and dashboard implementation.
- Maintaining every old command, import, config schema, execution environment, lock or checkpoint as runnable in the new system.
- Deleting historical source, outputs or active resources; overwriting evidence; rewriting old provenance to manufacture compatibility.
- Generic framework layers, speculative plugin architecture, tensor wrappers, extra commands for every internal function, and unnecessary installation infrastructure.
- Renaming the repository directory or treating a directory move alone as sufficient separation of responsibilities.

## Further Notes

- The user confirmed shared understanding in Q13 after accepting migration-before-additions, no source-directory wrapper, responsibility-oriented organization, preserved legacy evidence and simple replacement commands.
- Interview language is Thai; durable specifications and new documentation remain English. No new domain glossary entries are necessary for generic architecture terms.
- This feature's local issue-tracker status is `ready-for-agent`. Publishing the spec does not start code changes, run acceptance checks or create new experimental evidence.
- [ADR 0001: scientific and phase decisions](../../docs/adr/0001-query-efficiency-and-unseen-attack-evaluation.md)
- [ADR 0002: upstream fixed-baseline preservation](../../docs/adr/0002-preserve-upstream-fixed-kernel-baselines.md)
- [ADR 0003: accepted architecture decision](../../docs/adr/0003-restructure-active-code-and-archive-legacy-detectors.md)
- [Project glossary](../../GLOSSARY.md)
- [Accepted architecture plan and source/archive mappings](../deep-kernel-phase1/architecture-plan.md)
- [Architecture interview history](../deep-kernel-phase1/architecture-interview.md)
- [Phase 1 scientific spec and subsequent five-method work](../deep-kernel-phase1/spec.md)
