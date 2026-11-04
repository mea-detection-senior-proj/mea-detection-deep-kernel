# Model Extraction Traffic Detection

Active research code lives in the root-level `mea_detection/` Python package.
It compares fixed RBF MMD, fixed Multi-RBF MMD, and pure-trained deep-kernel MMD
on shared frozen embeddings, purpose-separated partitions and shared draws.
The structural migration does not complete the five-method Phase 1 benchmark.

## Run from the repository root

Install dependencies with `python -m pip install -r requirements.txt`.
Use your Python environment; on Windows this checkout uses
`.\.venv\Scripts\python.exe` in place of `python`.
Provision an encoder locally under `artifacts/models/bge-small-en-v1.5`, or supply
another local folder with `--embedding-model`. Remote encoders require a pinned
40-character commit in `embedding_revision`.

```powershell
# Validate capacity without encoding, GPU allocation or run artifacts.
python -m mea_detection run --config configs/experiments/deep_pure.json --dry-run

# Prepare shared evidence, fit selected methods, calibrate, evaluate and report.
# Every run requires a NEW output directory.
python -m mea_detection run --config configs/experiments/deep_pure.json --output artifacts/migrated_comparison_v1

# Inspect data without loading an encoder; writes an audit, not a detector run.
python -m mea_detection audit --data-root data --output artifacts/migrated_audit_v1

# Prepare a protocol for reuse by multiple method runs.
python -m mea_detection prepare --config configs/experiments/deep_pure.json --output artifacts/migrated_protocol_v1

# Regenerate a report from saved results without training or encoding.
python -m mea_detection report --runs artifacts/migrated_comparison_v1/results --output artifacts/migrated_report_v1

# Active tests only; archived environments and test suites are excluded.
python -m unittest discover -s tests -v
```

See [current commands and configuration](docs/RUN_EXPERIMENTS.md) and the
[migration record, validation and limitations](docs/CLEAN_ARCHITECTURE_MIGRATION.md).

## Repository structure

```text
mea_detection/
  data/              query readers, grouping, partitions, windows and audit
  embeddings/        frozen encoder and content-addressed cache
  detection/         fitting, scoring and separate checkpoint persistence
    kernels/         shared fixed and deep-kernel calculations
  evaluation/        calibration, rates and empirical endpoint rules
  experiments/       one workflow, protocol policy and artifact adapters
  reporting/         validation and rendering of saved evidence
  cli/               command parsing and composition
configs/             active experiment configurations
data/                research inputs (preserved in place)
artifacts/           local encoders, caches, protocols and runs
old-detectors/       preserved legacy source, outputs and provenance index
tests/               active numerical, workflow and command checks
docs/                current usage, decisions and historical notes
```

Numerical modules use Torch and NumPy directly. They do not load encoders,
select datasets, write reports or serialize checkpoints. See the migration record
for enforced dependency boundaries.

## Data and scientific scope

Place queries under `data/<dataset>/normal/queries.jsonl` and
`data/<dataset>/attacker/queries.jsonl`; each row needs nonempty string `id` and
`query` fields. Dataset folders need no registry. Processed source data are
available from [Hugging Face](https://huggingface.co/datasets/ShuzeLiu11/mmd-llm-mea-detection-data).
Their licenses and terms apply separately.

The active workflow uses an adapted common evaluation protocol. It preserves
fixed-baseline computations but is not an unchanged reproduction of the original
paper's complete sampling and calibration protocol. Always distinguish calibration
target FPR from measured FPR. See [scientific decisions](docs/adr/0001-query-efficiency-and-unseen-attack-evaluation.md)
and [baseline preservation and known edge differences](docs/adr/0002-preserve-upstream-fixed-kernel-baselines.md).
Learned-bandwidth RBF and the MLP classifier remain subsequent work.

## Original implementation and evidence

This repository began with the official implementation of
**An Embarrassingly Simple Detector for Model Extraction Attacks in Large Language Model API Traffic**.
The [archive index](old-detectors/INDEX.md) records where the original MMD,
PRADA, SEAT, CAP, DATE, Mahalanobis, pseudo-energy, Pilot and paper runners moved.
The complete [pre-migration README](old-detectors/README_PRE_MIGRATION.md) preserves
historical commands and result descriptions. Those paths are historical and the
archived commands are not maintained as active entry points.

[Paper](https://arxiv.org/abs/2606.05725)

```bibtex
@misc{liu2026embarrassinglysimpledetectormodel,
  title={An Embarrassingly Simple Detector for Model Extraction Attacks in Large Language Model API Traffic},
  author={Shuze Liu and Qianwen Guo and Yushun Dong},
  year={2026},
  eprint={2606.05725},
  archivePrefix={arXiv},
  primaryClass={cs.CR},
  url={https://arxiv.org/abs/2606.05725}
}
```

Code is released under the [MIT License](LICENSE).
