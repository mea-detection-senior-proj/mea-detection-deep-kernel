# Legacy source and evidence archive

Relocated on 2026-11-04 under the accepted Clean Architecture migration.
The source checkout before migration was
`59d626d7a325425ab7e81a666ca6c3140eb82bb8`; its tracked working tree was clean.
The inventory also includes local ignored outputs, caches and bytecode that were
present at relocation. These local files remain on disk; Git ignore rules still
apply, so they are not all distributable in a fresh checkout.

Each path below moved intact beneath `old-detectors/`, preserving its internal
layout. [manifest.json](manifest.json) lists all 1,267 original and archived paths,
byte sizes and SHA-256 hashes captured before relocation. The complete inventory
was verified after relocation. No historical scientific identity records were
rewritten. [README_PRE_MIGRATION.md](README_PRE_MIGRATION.md) retains prior commands
and output descriptions; its paths describe the pre-migration checkout.

| Original root path | Archived path | Purpose and provenance |
| --- | --- | --- |
| `MMD_detection/` | [MMD_detection/](MMD_detection/) | Complete original MMD implementation and associated files; independent numerical reference for active fixed kernels. |
| `pilot/` | [pilot/](pilot/) | Exploratory deep-kernel workflow, tests and historical local outputs; superseded by the active workflow. |
| `PRADA/` | [PRADA/](PRADA/) | Original/adapted PRADA reference implementation. |
| `SEAT/` | [SEAT/](SEAT/) | Original/adapted SEAT reference implementation. |
| `CAP/` | [CAP/](CAP/) | Coverage-based legacy detector. |
| `DATE/` | [DATE/](DATE/) | Legacy text anomaly detector. |
| `Mahalanobis/` | [Mahalanobis/](Mahalanobis/) | Legacy marginal Mahalanobis detector. |
| `PseudoEnergy/` | [PseudoEnergy/](PseudoEnergy/) | Legacy pseudo-class energy detector. |
| `new_main_experiment/` | [new_main_experiment/](new_main_experiment/) | Historical multi-method paper runner and associated files. |
| `review_experiment/` | [review_experiment/](review_experiment/) | Historical adaptive-evasion and reference-contamination experiments. |
| `supplementary_experiments/` | [supplementary_experiments/](supplementary_experiments/) | Historical sensitivity/runtime launch tooling and outputs. |
| `run_all_paper_experiments.sh` | [run_all_paper_experiments.sh](run_all_paper_experiments.sh) | Legacy batch launcher; paths are historical. |
| `query_extracter/` | [query_extracter/](query_extracter/) | Standalone stored-query conversion tools, not a detector or active benchmark dependency. |
| `experiment_result/` | [experiment_result/](experiment_result/) | Historical experiment output collection, retained with legacy context. |

The original MMD source provenance is documented in
[ADR 0002](../docs/adr/0002-preserve-upstream-fixed-kernel-baselines.md): upstream
commit `7532c25b973ef13f3f971e73a40ff46d469e3fea`, normalized Git blob
`25844d41a113dfc520c4fbcb136afda82babc841`. The active numerical test reads this
preserved source explicitly by path. Active runtime never imports the archive.

Historical execution environments and commands are not maintained. Relative paths
may no longer work, and dependencies may differ. Archive contents are reference
material; use [current commands](../docs/RUN_EXPERIMENTS.md) for active work.
Normal tests run under `tests/`; archived test suites are excluded.

Protected resources remain at the root: `data/`, `artifacts/models/`, embedding
caches and retained protocols/results, including `artifacts/model_leeching_protocol_v1`.
A historical protocol's incompatibility does not make it unused or authorize
deleting or rewriting it.
