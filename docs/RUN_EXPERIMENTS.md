# Active experiment commands

Run commands at the repository root with `python -m mea_detection`. On this
Windows checkout, substitute `.\.venv\Scripts\python.exe` for `python`.
The active package is intentionally usable without installation metadata.

## Configuration and preflight

`configs/experiments/deep_pure.json` selects all three current methods. The
`mmd_smoke.json` and `mmd_comparison.json` examples select fixed kernels.
Explicit flags override only supplied configuration fields. Training overrides
merge with existing training settings; `--window` changes evaluation size, while
`--train-window` changes training pair size.

```powershell
python -m mea_detection run --config configs/experiments/deep_pure.json --window 100 --seed 42 --device cpu --output artifacts/migrated_cpu_v1 --dry-run
```

Preflight checks configuration, output destination, partition capacity and any
requested protocol's integrity. It neither loads an encoder nor allocates GPU
resources nor creates run artifacts. It does not prove GPU availability.
Audit needs no encoder configuration:

```powershell
python -m mea_detection audit --data-root data --output artifacts/migrated_readiness_v1
```

Audit writes readiness records only. It checks local data, duplicate/group
separation and capacity; it does not measure detector performance. Every output
directory must be new, including audit and report destinations.

## Full workflow and shared protocol

```powershell
python -m mea_detection run --config configs/experiments/deep_pure.json --output artifacts/migrated_three_methods_v1
```

The workflow prepares `protocol/`, fits selected methods into `results/`, and
derives `report/` from saved scores. `run.json` records running, complete or failed
state. A failed directory remains evidence and must not be reused as a new output.
Frozen selected deep-kernel checkpoints live at `results/seed_<seed>/deep_kernel.pt`.

To prepare once and reuse shared partitions, embeddings and draws:

```powershell
python -m mea_detection prepare --config configs/experiments/deep_pure.json --output artifacts/migrated_shared_protocol_v1
python -m mea_detection run --config configs/experiments/deep_pure.json --protocol-lock artifacts/migrated_shared_protocol_v1 --methods rbf multi_rbf --output artifacts/migrated_fixed_v1
python -m mea_detection run --config configs/experiments/deep_pure.json --protocol-lock artifacts/migrated_shared_protocol_v1 --methods deep_kernel --output artifacts/migrated_deep_v1
python -m mea_detection report --runs artifacts/migrated_fixed_v1/results artifacts/migrated_deep_v1/results --output artifacts/migrated_combined_report_v1
```

Use matching data, encoder, precision, seeds, evaluation grid and sampling settings
when reusing a protocol. Source mismatch or altered locked files fails explicitly.
The saved embedding/pool/draw snapshot is the evaluation input on reuse; editing
raw data or encoder files does not update that snapshot. Prepare a fresh protocol
when inputs change. Cache keys include encoder content identity, revision, prefix,
normalization and query text. Generation remains float32; computation may use
float32 or float64 according to `dtype`.

## Reports and replay

```powershell
python -m mea_detection report --runs artifacts/migrated_three_methods_v1/results --output artifacts/migrated_rebuilt_report_v1
```

Reporting validates saved scores, calibrated thresholds, summaries, draw hashes,
source agreement, duplicate cells and declared coverage. It does not encode,
train, recalibrate or adjust thresholds from test outcomes. It can inspect saved
evidence from a different source revision when the run and lock agree; this does
not authorize executing that protocol with the current source.

Replay a new-system selected state in Python:

```python
from mea_detection.detection.checkpoints import load_detector
model = load_detector(checkpoint_path, device="cpu", expected_lock_id=lock_id)
# Supply prepared embeddings, the incoming window, and explicit reference indices.
score = model.score(reference_embeddings, window_embeddings, reference_indices)
```

Checkpoint format, active source and optional expected protocol identity are
checked. Parameters reload frozen with their saved dtype. Cross-version execution
of historical checkpoints is not guaranteed.

## Migration from old commands

| Former command | Replacement |
| --- | --- |
| `python -m experiments.run` | `python -m mea_detection run` |
| `python -m experiments.prepare` | `python -m mea_detection prepare` |
| `python -m experiments.audit_data` | `python -m mea_detection audit` |
| `python -m experiments.summarize_comparison` | `python -m mea_detection report` |

Old Python import paths are removed. The primary run operation always uses the
shared-protocol lifecycle; the former unlocked fixed-only runner was retired.
Config scientific values are preserved, including exploratory window size 250;
this migration does not silently substitute the subsequent Phase 1 primary grid.
The two examples named `*_locked.json` now request fresh protocol preparation and
new migrated destinations. Their names are historical. Recorded configurations,
locks and outputs under `artifacts/` are unchanged.

## Verification

```powershell
python -m unittest discover -s tests -v
```

`pytest.ini` also restricts pytest discovery to active tests, if pytest is installed.
Archived environments and test suites are not dependencies. The synthetic
three-method acceptance replaces only the external encoder and exercises actual
partitioning, training, checkpoint selection, calibration, persistence and reports.
See the [migration evidence](CLEAN_ARCHITECTURE_MIGRATION.md).
