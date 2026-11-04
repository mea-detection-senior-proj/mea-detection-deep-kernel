# Clean architecture interview

Date: 2026-11-04. Status: shared understanding confirmed in Q13; interview complete. The accepted [migration plan](architecture-plan.md) is ready for implementation planning/execution in a subsequent task. This interview did not start code migration.

Interview language: Thai. Durable documentation language: English.

## Accepted decisions

- Q1: Restructure all actively maintained code, including data preparation, detectors, training, experiments, reporting, and entry points. Keep the accepted scientific protocol and phase boundaries unchanged.
- Q2: Separate scientific calculations, experiment coordination, and external integrations. Scientific rules should be understandable and testable independently of CLI handling, configuration files, model downloads, and output storage. Introduce interfaces where something actually needs replacing.
- Q3: Preserve unused implementations in repository-root `old-detectors/` as reference material with provenance and instructions; maintaining their old execution environments is not required. Exclude archived code from normal execution and test discovery. Preserve active baseline methods and numerical checks against the original implementation.
- User accepted Q1–Q3 together. See [ADR 0003](../../docs/adr/0003-restructure-active-code-and-archive-legacy-detectors.md).
- Q4: Scientific calculations may use Torch/NumPy directly. Keep file access, encoder downloads, runtime device selection, and result persistence separate from those calculations.
- Q5: Archive unused legacy code and associated run outputs. The user approved this criterion rather than independently confirming every path; determine exact membership from active use and dependencies before migration.
- Q6: Commands and config formats may change; "Simple is key." Provide working examples and migration guidance rather than compatibility wrappers for every old command. Preserve scientific settings and meanings.
- Q7: Keep historical artifacts available for inspection without overwriting them. Old locks/checkpoints need not all resume in the new system. Reject incompatible identities explicitly; new-system checkpoints must save and reload correctly.
- Q8: The proposed `domain/application/adapters/cli` folder layout was not accepted. The user preferred folders organized by research responsibility and execution flow, including a `detection/` home for later method comparisons. Q13 resolves the revised layout; dependency separation remains accepted.
- Q9: Migrate the existing workflow first, preserving current behavior and uncommitted work. Add the two missing learned controls afterward, rather than mixing those additions into the structural migration.
- Q10: Provide one primary end-to-end command. Retain data audit, no-training preflight, shared protocol preparation, and report regeneration without retraining; do not expose every internal step as a command.
- Q11 follow-up: The user preferred a top-level code folder without a `src/` wrapper and suggested `mea-detection`. Q13 accepted `mea_detection` for Python imports; no repository-directory rename was requested.
- Q12: The first migration milestone ends with the existing three methods working in the new structure, unused legacy code/results archived, and usage documentation updated. The learned-bandwidth RBF and MLP classifier are a separate subsequent milestone. Migration acceptance covers original-baseline numerical checks, synthetic end-to-end workflow, checkpoint save/reload, protocol integrity, and report generation; a complete real-data benchmark is not required to establish the structural migration.

- Q13: The user explicitly confirmed shared understanding: one root `mea_detection/` package without `src/`, with `data`, `embeddings`, `detection/kernels`, `evaluation`, `experiments`, `reporting`, and `cli`; protected active data/model/cache resources; archived unused code and associated outputs; simple replacement commands/config; migration acceptance before the later learned-controls/benchmark milestone. Finalizing the English documents does not start code migration.

## Design tree closure

- Active-code organization, dependency policy and responsibility ownership: accepted through Q4/Q13; see the migration plan for enforceable rules.
- Archive criterion, source inventory, protection of active resources and numerical reference loading: resolved through user policy plus read-only dependency inspection. Recheck actual references during implementation rather than guessing about changed files.
- Compatibility: accepted in Q6/Q7. Reuse artifact conventions; validate identities explicitly and reject incompatible reuse. No universal old-command or old-lock resume guarantee.
- Ordering, first-milestone completion scope and acceptance evidence: accepted in Q9/Q12.
- Final shared-understanding review: confirmed in Q13. No unresolved user-level design decisions remain for the structural milestone. Routine file splits and exact command flags are implementation choices within the accepted plan.

## Repository facts from read-only inspection

- The active CLI/workflow already exists in `experiments/run.py`, `workflow.py`, and `locked.py`. Reuse its behavior rather than creating a competing orchestration framework.
- Scientific calculations use Torch; splitting and sampling use NumPy. A fully library-free scientific layer would require more than moving files.
- `tests/test_mmd_pipeline.py` imports the retained original MMD script for differential verification; moving that source requires updating test loading.
- Legacy experiment scripts contain paths tied to their current locations. Archiving source does not preserve runnable commands automatically.
- Code identity includes source paths/content. Package moves affect identity; old protocol locks must not silently become compatible.
- The working tree already has uncommitted implementation changes. Preserve these during any later migration.
- `docs/RESTRUCTURING_PLAN_TH.md` contains older location and migration guidance superseded by ADR 0003. Its earlier scientific proposals are governed by ADR 0001 and the accepted spec.
