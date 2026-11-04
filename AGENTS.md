## Agent skills

### Issue tracker

Issues and specs live as local Markdown files under `.scratch/<feature>/`.
Before creating, reading, or updating tickets, read `docs/agents/issue-tracker.md`.

### Triage labels

Use the five default triage roles as local issue statuses.
Before triaging issues, read `docs/agents/triage-labels.md`.

### Domain docs

Single-context layout: root `GLOSSARY.md` and `docs/adr/`.
Before exploring the codebase, read `docs/agents/domain.md`.

## Active architecture and archive

Maintain active Python code in the root-level `mea_detection/` package.
Before changing module boundaries, workflow behavior, or archive contents, read
`docs/adr/0003-restructure-active-code-and-archive-legacy-detectors.md` and
`docs/CLEAN_ARCHITECTURE_MIGRATION.md`.

Active runtime and configs must remain independent of `old-detectors/`.
Keep archived source and historical outputs as reference evidence. The only
permitted execution of archived code in active tests is the explicit file-based
upstream MMD numerical comparison in `tests/test_mmd_pipeline.py`; archive
integrity tests may read files to verify hashes. Exclude archived test suites
from normal discovery.

Preserve research inputs in `data/` and active models, embedding caches, protocols
and results in `artifacts/`. Use new output destinations; retain historical
identity records and reject incompatible reuse rather than rewriting them.

For run commands and replacement configs, read `docs/RUN_EXPERIMENTS.md`.
Run active checks with `python -m unittest discover -s tests -v`;
`tests/test_architecture.py` enforces dependency boundaries and archive integrity.
