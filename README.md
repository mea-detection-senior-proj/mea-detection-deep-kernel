# MMD-LLM-MEA-Detection

[Paper](https://arxiv.org/abs/2606.05725)

Official implementation and processed query-traffic artifact for:

**An Embarrassingly Simple Detector for Model Extraction Attacks in Large Language Model API Traffic**

This repository provides code for benign-calibrated detection of LLM model extraction attacks in API query traffic.
The main detector applies maximum mean discrepancy (MMD) to sentence embeddings and compares incoming traffic windows against benign reference traffic.
The artifact also includes adapted and original-protocol baselines used in the paper: PRADA, SEAT, CAP, DATE, marginal Mahalanobis distance, and pseudo-class energy.

## Citation

If you find this repository useful, please cite our paper:

```bibtex
@misc{liu2026embarrassinglysimpledetectormodel,
      title={An Embarrassingly Simple Detector for Model Extraction Attacks in Large Language Model API Traffic}, 
      author={Shuze Liu and Qianwen Guo and Yushun Dong},
      year={2026},
      eprint={2606.05725},
      archivePrefix={arXiv},
      primaryClass={cs.CR},
      url={https://arxiv.org/abs/2606.05725}, 
}
```

## Overview

The repository supports the experiments in the paper:

- **Proposed detector:** benign-calibrated MMD over semantic query embeddings.
- **Unified adapted baselines:** PRADA, SEAT, CAP, DATE, Mahalanobis, and pseudo-class energy evaluated under a shared traffic-window protocol.
- **Original-protocol baselines:** baseline-specific protocols used to study whether prior methods transfer directly to text-query model extraction traffic.
- **Additional analyses:** adaptive evasion, benign-reference contamination, encoder/batch/threshold sensitivity, decision-direction sensitivity, and runtime.

The default setting uses `BAAI/bge-small-en-v1.5` as the sentence embedding model and evaluates both pure attacker traffic and mixed benign-attacker traffic windows.

## Repository Structure

```text
MMD_detection/              # proposed benign-calibrated MMD detector
PRADA/                      # PRADA-style adapted and stream detectors
SEAT/                       # SEAT-style adapted and original account detectors
CAP/                        # CAP-style coverage detector
DATE/                       # DATE-style text anomaly detector
Mahalanobis/                # marginal Mahalanobis detector
PseudoEnergy/               # pseudo-class energy baseline
new_main_experiment/        # main multi-method experiment driver
review_experiment/          # adaptive evasion and reference contamination experiments
query_extracter/            # adaptive MeaeQ query generation utilities
data/                       # processed query files; see Data Preparation
supplementary_experiments/  # sensitivity, decision-direction, and runtime scripts
run_all_paper_experiments.sh  # convenience entry point for paper experiments
requirements.txt            # shared Python dependencies
```

## Installation

Install the shared dependencies from the repository root:

```bash
pip install -r requirements.txt
```

GPU execution is recommended for embedding, MMD, and nearest-neighbor computations.

## Data Preparation

The processed query data are hosted on Hugging Face:

```text
https://huggingface.co/datasets/ShuzeLiu11/mmd-llm-mea-detection-data
```

Download the dataset into the repository root before running experiments:

```bash
hf download ShuzeLiu11/mmd-llm-mea-detection-data \
  --repo-type dataset \
  --local-dir data
```

Alternatively, clone the dataset repository directly:

```bash
git clone https://huggingface.co/datasets/ShuzeLiu11/mmd-llm-mea-detection-data data
```

Each dataset is stored in JSONL format:

```text
data/<dataset>/normal/queries.jsonl
data/<dataset>/attacker/queries.jsonl
```

Each row contains a `query` field:

```json
{"id": "example-0", "index": 0, "query": "What is the capital of France?"}
```

## Reproducing Paper Experiments

All commands below assume that the Hugging Face dataset has been downloaded to `data/` as described above.
Most experiments use the paper defaults: `BAAI/bge-small-en-v1.5`, batch size 1,500, 50 benign/pure/mixed evaluation windows, mixed attacker fractions `0.05,0.10,0.25,0.50`, and a 95th-percentile benign-calibrated threshold.

### Unified entry point

All paper experiments are launched through `run_all_paper_experiments.sh`.
Running it without arguments executes every experiment group in sequence:

```bash
bash run_all_paper_experiments.sh
```

To run selected groups, set `EXPERIMENTS`, for example:

```bash
EXPERIMENTS="main adaptive contamination" bash run_all_paper_experiments.sh
```

Available groups are listed below. Each command can be run independently from the repository root through the same entry point:

```bash
# Main paper results: MMD and six adapted baselines on 14 datasets and seeds 1, 20, 42
EXPERIMENTS=main bash run_all_paper_experiments.sh

# Original-protocol transfer analysis for prior baselines
EXPERIMENTS=original_protocol bash run_all_paper_experiments.sh

# Adaptive evasion analysis on original, regularized, and projection MeaeQ/SST-2 queries
EXPERIMENTS=adaptive bash run_all_paper_experiments.sh

# Benign-reference contamination analysis at 1%, 5%, and 10%
EXPERIMENTS=contamination bash run_all_paper_experiments.sh

# Sentence-encoder sensitivity analysis
EXPERIMENTS=encoder_sensitivity bash run_all_paper_experiments.sh

# MMD batch-size and threshold-percentile sensitivity analysis
EXPERIMENTS=batch_threshold_sensitivity bash run_all_paper_experiments.sh

# One-sided vs two-sided decision-rule analysis for adapted baselines
EXPERIMENTS=decision_direction bash run_all_paper_experiments.sh

# Cold-cache wall-clock runtime analysis
EXPERIMENTS=runtime bash run_all_paper_experiments.sh

# MMD reference-repeat sensitivity appendix
EXPERIMENTS=mmd_reference_repeats bash run_all_paper_experiments.sh

# MMD null-sample sensitivity appendix
EXPERIMENTS=mmd_null_samples bash run_all_paper_experiments.sh
```

The full command can be time-consuming because it includes DATE training and multiple datasets/seeds.
For a quick smoke run, still use the same entry point while restricting datasets, seeds, and methods:

```bash
DATASETS=model_leeching SEEDS=42 METHODS="MMD PseudoEnergy" \
EXPERIMENTS=main bash run_all_paper_experiments.sh
```

The entry point dispatches to the corresponding experiment code and writes result files under each experiment directory.
It may also create local `logs/`, `outputs/`, and `cache/` directories during execution.

## Configuration

The unified entry point accepts the following environment variables:

```bash
DATASET=model_leeching
DATASETS=model_leeching,Query_efficent_med,Meaeq_HATESPEECH
BATCH_SIZE=1500
SEED=42
DEVICE=cuda
OUTPUT_ROOT=<output-directory>
```

## Method Notes

The adapted protocol uses the same processed query datasets and the same traffic-window construction across methods.
Benign queries are split into a benign reference/calibration pool and a held-out benign evaluation pool.
Attacker queries are used to construct pure attacker windows and mixed windows with attacker fractions such as `0.05`, `0.10`, `0.25`, and `0.50`.

MMD calibrates a benign-only null distribution using benign-vs-benign comparisons.
PRADA scores nearest-neighbor distance normality.
SEAT scores similar-pair behavior.
CAP scores embedding-space coverage.
DATE scores text anomalies using self-supervised transformer objectives.
Mahalanobis scores distance from an estimated benign embedding distribution.

## Outputs

The unified entry point writes each experiment group to a separate directory.
Aggregate CSV files are the easiest files to inspect first; per-run output directories contain detector-level files such as `metadata.json`, `batch_scores.csv`, and, for query-level original protocols, `query_scores.csv`.

| Experiment group | Main outputs |
| --- | --- |
| `main` | Aggregate CSVs in `new_main_experiment/results/`: `new_main_experiment_runs_bs1500.csv` and `new_main_experiment_overall_bs1500.csv`. Per-method/per-dataset outputs are under `new_main_experiment/outputs/`, with logs in `new_main_experiment/logs/`. |
| `original_protocol` | Original-protocol detector outputs under `PRADA/stream_outputs/`, `SEAT/original_outputs/`, `CAP/outputs_original/`, `DATE/original_outputs_2/`, and `Mahalanobis/sample_outputs/`. Each dataset directory contains the corresponding `metadata.json` and score files. |
| `adaptive` | MMD outputs for original, regularized, and projection MeaeQ/SST-2 traffic under `review_experiment/MeaeQ_adaptive/MMD_result/<dataset>_bge_bs1500/`, with logs in `review_experiment/MeaeQ_adaptive/logs/`. |
| `contamination` | One output directory per dataset/seed under `review_experiment/calibration_contamination/outputs/<dataset>_seed42_bs1500/`; each contains `summary.csv` plus per-contamination-ratio subdirectories with `metadata.json` and detector score files. Logs are under `review_experiment/calibration_contamination/logs/`. |
| `encoder_sensitivity` | Aggregate CSVs in `supplementary_experiments/mmd_embedding_model_experiment/results/`: `mmd_embedding_model_runs_bs1500.csv`, `mmd_embedding_model_overall_bs1500.csv`, and `mmd_embedding_model_by_dataset_bs1500.csv`. Per-run MMD outputs are under `supplementary_experiments/mmd_embedding_model_experiment/outputs/`. |
| `batch_threshold_sensitivity` | MMD sensitivity outputs under `experiment_results/MMD_gpu/batch_size_bs*/` and `experiment_results/MMD_gpu/threshold_*/`. Each setting contains per-dataset detector outputs. |
| `decision_direction` | One-sided/two-sided baseline outputs under `supplementary_experiments/decision_direction_experiment/outputs/`, organized by decision side, method, and dataset. Logs are under `supplementary_experiments/decision_direction_experiment/logs/`. |
| `runtime` | Runtime CSVs in `supplementary_experiments/cold_cache_wallclock/results/`, named like `cold_cache_wallclock_<dataset>_bs1500_seed42.csv`, plus timed per-method outputs under `supplementary_experiments/cold_cache_wallclock/outputs/`. |
| `mmd_reference_repeats` | Aggregate CSVs in `supplementary_experiments/mmd_reference_repeats_experiment/results/`: `mmd_reference_repeats_runs_bs1500.csv` and `mmd_reference_repeats_overall_bs1500.csv`. Per-run MMD outputs are under `supplementary_experiments/mmd_reference_repeats_experiment/outputs/`. |
| `mmd_null_samples` | Aggregate CSVs in `supplementary_experiments/mmd_null_samples_experiment/results/`: `mmd_null_samples_runs_bs1500.csv` and `mmd_null_samples_overall_bs1500.csv`. Per-run MMD outputs are under `supplementary_experiments/mmd_null_samples_experiment/outputs/`. |

The aggregate CSVs report the paper metrics: benign FPR, pure-attacker TPR, mixed-traffic TPR at each attacker fraction, average TPR, balanced accuracy, output directory, metadata path, log file, and run status when applicable.

## Contact

For questions about the code or experiments, please contact sl26u@fsu.edu.

## License

This code is released under the MIT License. See [LICENSE](LICENSE) for details.
Processed query data are distributed separately on Hugging Face; users should follow the licenses and terms of the original data sources.
