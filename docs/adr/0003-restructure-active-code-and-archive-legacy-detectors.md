---
status: accepted
---

# Restructure active research code and archive legacy detectors

On 2026-11-04, architecture interview Q1–Q3 accepted restructuring all actively maintained data preparation, detector, training, experiment, reporting, and entry-point code. Preserve the Phase 1 scientific protocol and the deferred Phase 2/3 scope in ADR 0001. Reuse the existing scientific behavior and experiment lifecycle while separating scientific calculations, experiment coordination, and external integrations; introduce interfaces where dependencies actually need replacing rather than wrapping every function.

Preserve unused implementations under the repository-root `old-detectors/` as reference material with provenance and documentation. Maintaining their original execution environments or integrating them into the active workflow is not required. Exclude archived code from normal execution and test discovery, while retaining numerical verification of active fixed-kernel baselines against the preserved original source as required by ADR 0002. The fixed RBF and Multi-RBF methods remain active comparators even if their original complete script is archived.

Interview Q4–Q7 accepted using Torch and NumPy directly for scientific calculations, while keeping file access, encoder downloads, runtime device selection, and result persistence outside those calculations. Simplicity takes priority over preserving old commands and config formats: these may change with working examples and migration documentation, without maintaining compatibility wrappers for every old entry point. Preserve scientific meanings and accepted settings.

The user approved archiving unused legacy code and its associated run outputs, subject to checking what remains in active use. Preserve historical evidence without overwriting it. Historical locks and checkpoints need not all resume in the new system; detect incompatibility rather than rewriting old identity records to make them pass. New-system checkpoints must remain replayable under their documented compatibility rules.

Interview Q9–Q10 accepted migrating existing behavior before adding the two missing learned controls. Preserve existing uncommitted work. Provide one primary end-to-end command with focused support for data auditing, preflight without training, shared protocol preparation, and report regeneration without retraining; avoid a command for every internal step.

Q12 defines the first milestone as migration of the existing three methods, archiving unused legacy code and associated outputs, and updating usage documentation. Verify baseline numerics, synthetic end-to-end behavior, checkpoint save/reload, protocol integrity, and report generation. The full real-data benchmark and the two additional learned controls are not prerequisites for completing this structural milestone; the five-method Phase 1 benchmark remains subsequent work.

Q13 confirmed the final design: one root-level `mea_detection/` package, without `src/`, organized as `data`, `embeddings`, `detection/kernels`, `evaluation`, `experiments`, `reporting`, and `cli`. Architectural separation is enforced through dependency rules and focused interfaces rather than folders named after layers. The project may be called `mea-detection`; Python imports use the underscore spelling. This does not require renaming the repository directory.

This chooses a broader migration over retaining the current package layout. It supersedes the location and incremental-only restructuring guidance in `docs/RESTRUCTURING_PLAN_TH.md`; the accepted Phase 1 spec and ADR 0001 govern scientific scope. The [accepted migration plan](../../.scratch/clean-architecture/architecture-plan.md) records dependencies, source/archive mappings, compatibility and acceptance evidence. Shared understanding is confirmed; this documentation-only interview did not start code migration.

The implementation handoff is the [Clean Architecture spec](../../.scratch/clean-architecture/spec.md), published with status `ready-for-agent`.
