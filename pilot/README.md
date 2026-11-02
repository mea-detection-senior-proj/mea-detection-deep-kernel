# Known-attack feasibility pilot

## Additional datasets

`Meaeq_SST-2` and `ME_BERT_sst2_wiki` are inspected, downloaded datasets.
Pinned repository revision and file SHA256 hashes are recorded in
`ADDITIONAL_DATA_PROVENANCE.json`. `ADDITIONAL_DATA_AUDIT.json` records all
three split seeds and available class sizes. Run the audit alone with:

```powershell
.\.venv\Scripts\python.exe pilot/run_additional.py --audit-only
```

Run both datasets with the same six-case settings as model_leeching and
produce the combined method-first report:

```powershell
.\.venv\Scripts\python.exe -u pilot/run_additional.py
```

The two additional artifacts provide synthetic per-row IDs, index and query,
not source-passage provenance. Their splits link shared IDs and normalized
text, remove cross-label text collisions and deduplicate within each label.
This is an explicit ID/text-grouped protocol, not verified source-independent
evaluation. `model_leeching` retains its existing strict context parser and
source grouping. All datasets are trained and evaluated separately. The two
SST-2 benign pools overlap (see audit); this is not unseen-family testing.

The combined report is `MULTI_DATASET_RESULTS_TH.md`, with Method, Dataset,
Seed, Window, FPR, TPR 5%, TPR 10% at the top. Each dataset has its own
report, CSVs, charts, checkpoints and code snapshot under
`outputs/main_<dataset>_repeats20/`. Existing output folders are refused.
Individual runs use `run_known_pilot.py --dataset <name> --output <new-path>`;
individual summaries use `summarize_main.py <path> --dataset <name>`.

## Locked model_leeching experiment

Run the six-case comparison (seeds 1/20/42, windows 250/500) with 20
references in both calibration and test:

```powershell
.\.venv\Scripts\python.exe -u pilot/run_known_pilot.py
.\.venv\Scripts\python.exe pilot/summarize_main.py pilot/outputs/main_model_leeching_repeats20
```

The runner explicitly uses 20 epochs, 8 training windows per epoch, 32
validation windows, 200 calibration windows, and 100 test windows per
condition. The underlying pilot fixes training windows at 100 queries with
10% attacks; test conditions are benign, 5%, and 10% attacks. Each method
uses identical evaluation windows and reference draws. Thresholds use each
method's 95th calibration percentile. Checkpoints use validation only.

Output directories must be new; completed runs are never overwritten.
Use `--output` to choose a new experiment directory. `--reference-repeats`
is configurable for separate experiments, but the main summary validator
requires the locked value of 20. The summary checks all six settings, split
audits, calibration thresholds and reported rates before producing
`REPORT.md`, `summary.csv`, `validated_runs.csv`, `training_history.csv` and
`rates.svg` and `training.svg`. Ranges between seeds are descriptive, not confidence intervals.

This experiment studies known-attack behavior with the existing exploratory
objective. Length-only diagnostics remain background limitations; they are
not part of this experiment's method comparison.

This is exploratory code, not the complete research protocol. It compares a
median-bandwidth RBF, the repository's four-bandwidth RBF, and a learned
kernel. The learned kernel multiplies the fixed multi-RBF kernel by an RBF on
a small network's output. It trains on 10% mixed windows with a stabilized
signal-to-noise objective; this is a power-motivated proxy, not a validated
estimate of test power. Encoder embeddings are fixed.

Training uses independent RNG streams for bandwidth, training, validation,
calibration and test. A fixed set of validation windows is used to choose the
best epoch, including epoch zero (the untrained network); the checkpoint is
then frozen before calibration and testing. The default is 32 validation
windows. The objective uses variation among sampled mixed windows rather than
an established MMD power variance estimator, and these windows overlap. A
higher validation objective does not establish improved detection at a fixed
FPR. This is an exploratory proxy that needs further research validation.

For `model_leeching`, benign and attack rows reuse
question IDs, and attack prompts contain source passages shared by multiple
questions. Before splitting, rows are joined transitively by shared ID,
normalized query text, and normalized attack source passage. Connected groups
are randomly allocated 40/20/20/20 to train, validation, calibration and test.
Cross-label normalized text collisions are removed and same-label text is
deduplicated. Attacks in the calibration partition are reserved and unused.
The script fails if IDs or expected attack source passages cannot be parsed.
Each method uses identical test windows and reference draws and receives its
own threshold calibrated at the 95th percentile on the same held-out benign
calibration windows. `--reference-repeats` controls the number of benign
reference draws averaged for each window and applies to calibration and test.
With 20 repeats the test statistic uses the same number of reference draws as
the paper, but this protocol is not a reproduction of the paper: it uses a
separate source-grouped calibration pool and averages references during
calibration, whereas the paper calibrates using single benign-pair MMD scores
from its benign reference pool. Windows are sampled repeatedly, so rates are not based on
independent observations. The checks do not establish independence between
different source passages, detect paraphrases, or prove the meaning of IDs for
other datasets. This evaluates a known attack only. The prior
`known_attack_smoke` and `known_attack_gpu_smoke` results used text-only
splitting and should not be used as evidence of held-out performance.

From the repository root, with dependencies and the dataset installed:

```powershell
.\.venv\Scripts\python.exe pilot\deep_kernel_pilot.py `
  --dataset model_leeching --device cpu --window 250 `
  --embedding-model pilot/cache/bge-small-en-v1.5
```

Use `--device cuda` if the installed PyTorch supports the GPU. Outputs include
per-window scores, split hashes, settings, rates, training history and weights
in `pilot/outputs/known_attack`. Split hashes and the grouping audit are in
`metadata.json`. Set a different `--output` for each run. A capped run using
`--max-per-class` takes the first rows of each file and is only for smoke tests.
Before drawing research conclusions, add multiple seeds, source-aware splits,
uncertainty analysis, an unseen-family evaluation and systematic tuning.

For a direct exploratory comparison with 20 reference repeats:

```powershell
.\.venv\Scripts\python.exe pilot\deep_kernel_pilot.py `
  --device cuda --embedding-model pilot/cache/bge-small-en-v1.5 `
  --window 250 --seed 42 --reference-repeats 20 `
  --calibration-windows 200 --test-windows 50 `
  --output pilot/outputs/repeats20_bs250_seed42
```
